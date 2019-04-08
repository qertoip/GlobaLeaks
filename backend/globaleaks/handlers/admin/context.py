# -*- coding: utf-8
#
#   /admin/contexts
#   *****
# Implementation of the code executed on handler /admin/contexts
#
from six import text_type
from sqlalchemy.sql.expression import not_

from globaleaks import models
from globaleaks.handlers.admin.modelimgs import db_get_model_img
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.operation import OperationHandler
from globaleaks.models import fill_localized_keys, get_localized_values
from globaleaks.orm import transact
from globaleaks.rest import requests, errors


def admin_serialize_context(session, context, language):
    """
    Serialize the specified context

    :param session: the session on which perform queries.
    :param language: the language in which to localize data.
    :return: a dictionary representing the serialization of the context.
    """
    receivers = [r[0] for r in session.query(models.ReceiverContext.receiver_id)
                                      .filter(models.ReceiverContext.context_id == context.id)
                                      .order_by(models.ReceiverContext.presentation_order)]
    picture = db_get_model_img(session, 'contexts', context.id)

    ret_dict = {
        'id': context.id,
        'status': context.status,
        'tip_timetolive': context.tip_timetolive,
        'select_all_receivers': context.select_all_receivers,
        'maximum_selectable_receivers': context.maximum_selectable_receivers,
        'show_recipients_details': context.show_recipients_details,
        'allow_recipients_selection': context.allow_recipients_selection,
        'show_small_receiver_cards': context.show_small_receiver_cards,
        'enable_comments': context.enable_comments,
        'enable_messages': context.enable_messages,
        'enable_two_way_comments': context.enable_two_way_comments,
        'enable_two_way_messages': context.enable_two_way_messages,
        'enable_attachments': context.enable_attachments,
        'enable_rc_to_wb_files': context.enable_rc_to_wb_files,
        'enable_scoring_system': context.enable_scoring_system,
        'score_threshold_medium': context.score_threshold_medium,
        'score_threshold_high': context.score_threshold_high,
        'score_receipt_text_custom': context.score_receipt_text_custom,
        'score_receipt_text_l': context.score_receipt_text_l,
        'score_receipt_text_m': context.score_receipt_text_m,
        'score_receipt_text_h': context.score_receipt_text_h,
        'score_threshold_receipt': context.score_threshold_receipt,
        'presentation_order': context.presentation_order,
        'show_receivers_in_alphabetical_order': context.show_receivers_in_alphabetical_order,
        'show_steps_navigation_interface': context.show_steps_navigation_interface,
        'questionnaire_id': context.questionnaire_id,
        'additional_questionnaire_id': context.additional_questionnaire_id,
        'receivers': receivers,
        'picture': picture
    }

    return get_localized_values(ret_dict, context, context.localized_keys, language)


@transact
def get_context_list(session, tid, language):
    """
    Returns the context list.

    :param session: the session on which perform queries.
    :param language: the language in which to localize data.
    :return: a dictionary representing the serialization of the contexts.
    """
    return sorted([admin_serialize_context(session, context, language)
                      for context in session.query(models.Context).filter(models.Context.tid == tid)],
                  key=lambda x: x['presentation_order'])


def db_associate_context_receivers(session, tid, context, receiver_ids):
    session.query(models.ReceiverContext).filter(models.ReceiverContext.context_id == context.id).delete(synchronize_session='fetch')

    if not receiver_ids:
        return

    if session.query(models.Context).filter(models.Context.id == context.id,
                                            models.Context.tid == models.UserTenant.tenant_id,
                                            models.User.id.in_(receiver_ids),
                                            models.UserTenant.user_id == models.User.id).count == 0:
        raise errors.InputValidationError()

    for i, receiver_id in enumerate(receiver_ids):
        session.add(models.ReceiverContext({'context_id': context.id,
                                            'receiver_id': receiver_id,
                                            'presentation_order': i}))

@transact
def get_context(session, tid, context_id, language):
    """
    Returns:
        (dict) the context with the specified id.
    """
    context = session.query(models.Context).filter(models.Context.tid == tid, models.Context.id == context_id).one()

    return admin_serialize_context(session, context, language)


def fill_context_request(tid, request, language):
    request['tid'] = tid
    fill_localized_keys(request, models.Context.localized_keys, language)

    if not request['allow_recipients_selection']:
        request['select_all_receivers'] = True

    request['tip_timetolive'] = 0 if request['tip_timetolive'] < 0 else request['tip_timetolive']

    if request['select_all_receivers']:
        request['maximum_selectable_receivers'] = 0

    return request


def check_context_questionnaire_association(session, tid, questionnaire_id):
    if session.query(models.Questionnaire).filter(models.Questionnaire.id == questionnaire_id,
                                                  not_(models.Questionnaire.tid.in_(set([1, tid])))).count():
        raise errors.InputValidationError()


def db_update_context(session, tid, context, request, language):
    request = fill_context_request(tid, request, language)

    check_context_questionnaire_association(session, tid, request['questionnaire_id'])

    context.update(request)

    db_associate_context_receivers(session, tid, context, request['receivers'])

    return context


def db_create_context(session, tid, request, language):
    request = fill_context_request(tid, request, language)

    check_context_questionnaire_association(session, tid, request['questionnaire_id'])

    context = models.db_forge_obj(session, models.Context, request)

    db_associate_context_receivers(session, tid, context, request['receivers'])

    return context


@transact
def create_context(session, tid, request, language):
    """
    Creates a new context from the request of a client.

    Args:
        (dict) the request containing the keys to set on the model.

    Returns:
        (dict) representing the configured context
    """
    context = db_create_context(session, tid, request, language)

    return admin_serialize_context(session, context, language)


@transact
def update_context(session, tid, context_id, request, language):
    """
    Updates the specified context. If the key receivers is specified we remove
    the current receivers of the Context and reset set it to the new specified
    ones.

    Args:
        context_id:

        request:
            (dict) the request to use to set the attributes of the Context

    Returns:
            (dict) the serialized object updated
    """
    context = models.db_get(session, models.Context, models.Context.tid == tid, models.Context.id == context_id)
    context = db_update_context(session, tid, context, request, language)

    return admin_serialize_context(session, context, language)


@transact
def order_elements(session, handler, req_args, *args, **kwargs):
    ctxs = session.query(models.Context).filter(models.Context.tid == handler.request.tid)

    id_dict = {ctx.id: ctx for ctx in ctxs}
    ids = req_args['ids']

    if len(ids) != len(id_dict) or set(ids) != set(id_dict):
        raise errors.InputValidationError('list does not contain all context ids')

    for i, ctx_id in enumerate(ids):
        id_dict[ctx_id].presentation_order = i


class ContextsCollection(OperationHandler):
    check_roles = 'admin'
    cache_resource = True
    invalidate_cache = True

    def get(self):
        """
        Return all the contexts.
        """
        return get_context_list(self.request.tid, self.request.language)

    def post(self):
        """
        Create a new context.
        """
        request = self.validate_message(self.request.content.read(),
                                        requests.AdminContextDesc)

        return create_context(self.request.tid, request, self.request.language)

    def operation_descriptors(self):
        return {
            'order_elements': (order_elements, {'ids': [text_type]}),
        }


class ContextInstance(BaseHandler):
    check_roles = 'admin'
    invalidate_cache = True

    def put(self, context_id):
        """
        Update the specified context.
        """
        request = self.validate_message(self.request.content.read(),
                                        requests.AdminContextDesc)

        return update_context(self.request.tid, context_id, request, self.request.language)

    def delete(self, context_id):
        """
        Delete the specified context.
        """
        return models.delete(models.Context, models.Context.tid == self.request.tid, models.Context.id == context_id)
