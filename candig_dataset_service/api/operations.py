"""
Methods to handle incoming service requests
"""

import json
import datetime
import pkg_resources
import uuid
import flask

from flask import Response, jsonify
from sqlalchemy import exc, or_
from pronto import Ontology

from candig_dataset_service.orm.models import Dataset, ChangeLog
from candig_dataset_service.orm import get_session, ORMException, dump
from candig_dataset_service.api.logging import apilog, logger
from candig_dataset_service.api.logging import structured_log as struct_log
from candig_dataset_service.api.models import BasePath, Version
from candig_dataset_service.api.exceptions import IdentifierFormatError
from candig_dataset_service.ontologies.duo import OntologyParser, OntologyValidator, ont




APP = flask.current_app


def _report_search_failed(typename, exception, **kwargs):
    """
    Generate standard log message + request error for error:
    Internal error performing search
    :param typename: name of type involved
    :param exception: exception thrown by ORM
    :param **kwargs: arbitrary keyword parameters
    :return: Connexion Error() type to return
    """
    report = typename + ' search failed'
    message = 'Internal error searching for '+typename+'s'
    logger().error(struct_log(action=report, exception=str(exception), **kwargs))
    return dict(message=message, code=500)


def _report_object_exists(typename, **kwargs):
    """
    Generate standard log message + request error for warning:
    Trying to POST an object that already exists
    :param typename: name of type involved
    :param **kwargs: arbitrary keyword parameters
    :return: Connexion Error() type to return
    """
    report = typename + ' already exists'
    logger().warning(struct_log(action=report, **kwargs))
    return dict(message=report, code=405)


def _report_update_failed(typename, exception, **kwargs):
    """
    Generate standard log message + request error for error:
    Internal error performing update (PUT)
    :param typename: name of type involved
    :param exception: exception thrown by ORM
    :param **kwargs: arbitrary keyword parameters
    :return: Connexion Error() type to return
    """
    report = typename + ' updated failed'
    message = 'Internal error updating '+typename+'s'
    logger().error(struct_log(action=report, exception=str(exception), **kwargs))
    return dict(message=message, code=500)


def _report_conversion_error(typename, exception, **kwargs):
    """
    Generate standard log message + request error for warning:
    Trying to POST an object that already exists
    :param typename: name of type involved
    :param exception: exception thrown by ORM
    :param **kwargs: arbitrary keyword parameters
    :return: Connexion Error() type to return
    """
    report = 'Could not convert '+typename+' to ORM model'
    message = typename + ': failed validation - could not convert to internal representation'
    logger().error(struct_log(action=report, exception=str(exception), **kwargs))
    return dict(message=message, code=400)


def _report_write_error(typename, exception, **kwargs):
    """
    Generate standard log message + request error for error:
    Error writing to DB
    :param typename: name of type involved
    :param exception: exception thrown by ORM
    :param **kwargs: arbitrary keyword parameters
    :return: Connexion Error() type to return
    """
    report = 'Internal error writing '+typename+' to DB'
    message = typename + ': internal error saving ORM object to DB'
    logger().error(struct_log(action=report, exception=str(exception), **kwargs))
    err = dict(message=message, code=500)
    return err


def log_outgoing(code, destination, path):
    APP.logger.info("{}: {} in {}. Sending to {}".format(
        APP.config['name'], code, path, destination
    ))

def get_headers():
    headers = {}
    try: 
        headers['X-Source']: APP.config['name']
    except KeyError:
        headers['X-Source']: 'candig_service'


@apilog
def post_dataset(body):
    db_session = get_session()

    print(APP.config)

    if not body.get('id'):
        iid = uuid.uuid1()
        body['id'] = iid
    else:
        iid = body['id']

    if not body.get('version'):
        body['version'] = Version

    body['created'] = datetime.datetime.utcnow()
    mapped = []

    if body.get('ontologies'):

        # Ontology objects should be {'id': ontology_name, 'terms': [{'id': 'some code'}]}

        mapped = {ontology['id']: ontology['terms'] for ontology in body['ontologies']}
        if 'duo' in mapped.keys():
            ov = OntologyValidator(ont=ont, input_json=mapped)
            valid, invalids = ov.validate_duo()
            if not valid:
                err = dict(message="DUO Validation Errors encountered: " + str(invalids), code=400)
                return err, 400 

            duo_terms = json.loads(ov.get_duo_list())

            duos = []

            for term in duo_terms:
                stuff = OntologyParser(ont, term["id"]).get_overview()
                duos.append({**term, **stuff})

            body['ontologies'] = duos
    body['ontologies_internal'] = mapped

    try:
        orm_dataset = Dataset(**body)
    except TypeError as e:
        err = _report_conversion_error('dataset', e, **body)
        return err, 400 

    try:
        db_session.add(orm_dataset)
        db_session.commit()
    except exc.IntegrityError:
        db_session.rollback()
        err = _report_object_exists('dataset: ' + body['id'], **body)
        return err, 405 
    except ORMException as e:
        db_session.rollback()
        err = _report_write_error('dataset', e, **body)
        return err, 500 

    body.pop('ontologies_internal')
    return body, 201 


@apilog
def get_dataset_by_id(dataset_id):
    """
    :param dataset_id:
    :return: all projects or if projectId specified, corresponding project
    """
    db_session = get_session()

    try:
        validate_uuid_string('id', dataset_id)
        specified_dataset = db_session.query(Dataset) \
            .get(dataset_id)
    except IdentifierFormatError as e:
        err = dict(
            message=str(e),
            code=404)
        return err, 404 

    if not specified_dataset:
        err = dict(message="Dataset not found: " + str(dataset_id), code=404)
        return err, 404 


    return dump(specified_dataset), 200 


@apilog
def delete_dataset_by_id(dataset_id):
    """

    :param dataset_id:
    :return:
    """
    db_session = get_session()

    try:
        specified_dataset = db_session.query(Dataset) \
            .get(dataset_id)
    except ORMException as e:
        err = _report_search_failed('call', e, dataset_id=str(dataset_id))
        return err, 500 

    if not specified_dataset:
        err = dict(message="Dataset not found: " + str(dataset_id), code=404)
        return err, 404 

    try:
        row = db_session.query(Dataset).filter(Dataset.id == dataset_id).first()
        db_session.delete(row)
        db_session.commit()
    except ORMException as e:
        err = _report_update_failed('dataset', e, dataset_id=str(dataset_id))
        return err, 500 

    return None, 204 


@apilog
def search_datasets(tags=None, version=None, ontologies=None):
    """
    :param tags:
    :param version:
    :return:
    """
    db_session = get_session()
    try:
        datasets = db_session.query(Dataset)
        if version:
            datasets = datasets.filter(Dataset.version.like('%' + version + '%'))
        if tags:
            # return any project that matches at least one tag
            datasets = datasets.filter(or_(*[Dataset.tags.contains(tag) for tag in tags]))
        if ontologies:
            # print(Dataset.ontologies_internal)
            datasets = datasets.filter(or_(*[Dataset.ontologies_internal.contains(term) for term in ontologies]))
    except ORMException as e:
        err = _report_search_failed('dataset', e)
        return err, 500 
    return [dump(x) for x in datasets], 200 


@apilog
def search_dataset_filters():
    """
    :return: filters for project searches
    """
    valid_filters = ["tags", "version"]

    return get_search_filters(valid_filters)


@apilog
def get_search_filters(valid_filters):
    filter_file = pkg_resources.resource_filename('candig_dataset_service',
                                                  'orm/filters_search.json')

    with open(filter_file, 'r') as ef:
        search_filters = json.load(ef)

    response = []

    for search_filter in search_filters:
        if search_filter["filter"] in valid_filters:
            response.append(search_filter)

    return response, 200 


@apilog
def search_dataset_ontologies():
    """
    Return all ontologies currently used by datasets
    """
    # print(flask.request.remote_addr, flask.request.headers)

    db_session = get_session()
    try:
        datasets = db_session.query(Dataset)

        valid = datasets.filter(Dataset.ontologies != [])

        ontologies = [dump(x)['ontologies'] for x in valid]

        terms = sorted(list(set([term['id'] for ontology in ontologies for term in ontology])))

    except ORMException as e:
        err = _report_search_failed('dataset', e)
        return err, 500 

    # log_outgoing(200, flask.request.headers['host'], flask.request.full_path)
    # return terms, 200 
    return terms, 200
    # print("Returning: {}".format(terms))
    # return jsonify(terms)


def search_dataset_discover(tags=None, version=None):
    err = dict(
        message="Not implemented",
        code=501
    )

    return err, 501


def get_datasets_discover_filters(tags=None, version=None):


    err = dict(
        message="Not implemented",
        code=501
    )
    return err, 501


@apilog
def post_change_log(body):
    db_session = get_session()
    change_version = body.get('version')

    body['created'] = datetime.datetime.utcnow()

    try:
        orm_changelog = ChangeLog(**body)
    except TypeError as e:
        err = _report_conversion_error('changelog', e, **body)
        return err, 400 

    try:
        db_session.add(orm_changelog)
        db_session.commit()
    except exc.IntegrityError:
        db_session.rollback()
        err = _report_object_exists('changelog: ' + body['version'], **body)
        return err, 405 
    except ORMException as e:
        err = _report_write_error('changelog', e, **body)
        return err, 500 

    logger().info(struct_log(action='post_change_log', status='created',
                             change_version=change_version, **body))

    return body, 201 


@apilog
def get_versions():
    """
    :return: release versions of the database
    """
    db_session = get_session()
    change_log = ChangeLog

    try:
        versions = db_session.query(change_log.version)
    except ORMException as e:
        err = _report_search_failed('versions', e)
        return err, 500 

    return [entry.version for entry in versions], 200 


@apilog
def get_change_log(version):
    """
    :param version: required release version
    :return: changes associated with specified release version
    """
    db_session = get_session()
    change_log = ChangeLog

    try:
        log = db_session.query(change_log)\
            .get(version)
    except ORMException as e:
        err = _report_search_failed('change log', e)
        return err, 500 

    if not log:
        err = dict(message="Change log not found", code=404)
        return err, 404 

    return dump(log), 200 


def validate_uuid_string(field_name, uuid_str):
    """
    Validate that the id parameter is a valid UUID string
    :param uuid_str: query parameter
    :param field_name: id field name
    """
    try:
        uuid.UUID(uuid_str)
    except ValueError:
        raise IdentifierFormatError(field_name)
    return

