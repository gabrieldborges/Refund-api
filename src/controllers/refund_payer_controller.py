# pylint: disable=duplicate-code
# Shares its response envelope with RefundCreatorController and its role-first
# guard with RefundReviewerController; both are deliberately identical rules.
from src.models.settings.unit_of_work import UnitOfWork
from src.models.repositories.interfaces.refunds_repository_interface import RefundsRepositoryInterface
from src.drivers.interfaces.file_storage_interface import FileStorageInterface
from src.controllers.interfaces.refund_payer_controller_interface import (
    RefundPayerControllerInterface,
)
from src.controllers.refund_serializer import format_refund_response
from src.controllers.file_cleanup import delete_quietly
from src.errors.types.http_forbidden_error import HttpForbiddenError
from src.errors.types.http_not_found_error import HttpNotFoundError
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError


class RefundPayerController(RefundPayerControllerInterface):
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        refunds_repository: RefundsRepositoryInterface,
        payment_storage: FileStorageInterface,
    ) -> None:
        self.__unit_of_work = unit_of_work
        self.__refunds_repository = refunds_repository
        self.__payment_storage = payment_storage

    async def pay(
        self,
        refund_id: int,
        payer_id: int,
        role: str,
        filename: str,
        content: bytes,
    ) -> dict:
        # Role first, before any database access. A check that never queries
        # cannot leak whether the id exists, so a standard user gets an
        # identical 403 for a real and for an invented id.
        if role != "admin":
            raise HttpForbiddenError("Only administrators can pay refunds")

        # Read WITHOUT a lock. select_for_update would hold a pool connection
        # while waiting; the conditional UPDATE below closes the race instead.
        refund = await self.__refunds_repository.select_refund_by_id(refund_id)

        if not refund:
            raise HttpNotFoundError("Refund not found")

        # BR-016 extended. A 403 is safe: whoever got here is an admin and, by
        # BR-012, already sees every refund, so nothing is left to leak.
        if refund["user"]["id"] == payer_id:
            raise HttpForbiddenError("You cannot pay your own refund")

        if refund["status"] != "approved":
            raise HttpUnprocessableEntityError("Only an approved refund can be paid")

        # The filename must exist before the UPDATE, so the file goes to disk
        # first. A crash between here and the UPDATE still orphans it — that is
        # Item 21, unresolved, and the UnitOfWork does NOT cover it: it bounds
        # the database transaction, and the filesystem is not part of it.
        stored_filename = self.__payment_storage.save(filename, content)

        # From here on, ANY failure leaves an orphaned file on disk unless we
        # compensate: not just the lost-race check below, but mark_as_paid,
        # insert_review or commit raising too. That is reachable, not
        # theoretical — the engine's global 3s lock_timeout (Task 2) can expire
        # with PostgreSQL's 55P03 lock_not_available while this UPDATE waits
        # for the row lock RefundReviewerController's select_for_update is
        # holding. A lock timeout is an ordinary infrastructure error, not "this
        # refund was not approved" — it must surface unchanged, not become a
        # 422, so we only compensate and re-raise, never swallow or translate.
        #
        # `committed` gates that compensation. The `async with` block covers
        # UnitOfWork.__aexit__ too, which runs AFTER a successful commit() to
        # close the session — and closing can itself raise (e.g. the same
        # dropped Neon connection that pool_pre_ping/pool_recycle exist to
        # handle). By the time that happens the row is already durably
        # committed with payment_filename = stored_filename, so deleting the
        # file would break a live reference instead of cleaning up a dead one.
        committed = False
        try:
            async with self.__unit_of_work as unit_of_work:
                affected = await unit_of_work.refunds.mark_as_paid(refund_id, stored_filename)

                if affected == 0:
                    # Another admin paid between our read and our write. A
                    # different message from the pre-write "not approved" guard
                    # above: this one is a lost race, not a status mismatch, and
                    # logs need to tell the two apart when auditing an orphan.
                    raise HttpUnprocessableEntityError(
                        "Refund was already paid by another admin"
                    )

                await unit_of_work.reviews.insert_review(
                    refund_id=refund_id,
                    reviewer_id=payer_id,
                    from_status="approved",
                    to_status="paid",
                    reason=None,
                )
                await unit_of_work.commit()
                committed = True
        except Exception:
            # Do NOT simplify this to an unconditional delete: once
            # `committed` is True the row already points at this file, and
            # deleting it here would destroy a valid payment receipt instead
            # of an orphaned one.
            if not committed:
                delete_quietly(
                    self.__payment_storage,
                    stored_filename,
                    "payment receipt, transaction failed",
                )
            raise

        # Re-read instead of patching the row we already have. The PATCH /status
        # endpoint built its response from a different repository and created the
        # divergent shape documented in UC-007; a new surface starts correct.
        paid_refund = await self.__refunds_repository.select_refund_by_id(refund_id)

        return format_refund_response(paid_refund)
