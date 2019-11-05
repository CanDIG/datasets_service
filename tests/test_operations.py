"""
Test suite to unit test operations
"""

import uuid
import flask
import os
import sys
import json
import pytest

sys.path.append("{}/{}".format(os.getcwd(), "candig_dataset_service"))
sys.path.append(os.getcwd())

from candig_dataset_service import orm
from candig_dataset_service.orm.models import Dataset
from candig_dataset_service.__main__ import app
from candig_dataset_service.api import operations
from candig_dataset_service.auth import auth_key
from candig_dataset_service.api.models import BasePath, Version


@pytest.fixture(name='test_client')
def load_test_client(db_filename="operations.db"):  # pylint: disable=too-many-locals
    # delete db if already exists and close session
    try:
        orm.close_session()
        os.remove(db_filename)

    except FileNotFoundError:
        pass
    except OSError:
        raise

    context = app.app.app_context()

    with context:
        orm.init_db('sqlite:///' + db_filename)

        data = orm.get_session().query(Dataset).all()
        print("PRIOR TO ADDING\n")
        print([d.id for d in data])

        print()

        dataset_1, dataset_2 = load_test_objects()

        app.app.config['BASE_DL_URL'] = 'http://127.0.0.1'

    return dataset_1, dataset_2, context


def test_post_dataset_exists(test_client):
    """
    post_dataset
    """
    ds1, ds2, context = test_client

    with context:
        _, code = operations.post_dataset({'id': ds1['id']})
        assert code == 405

def test_post_dataset_field_error(test_client):
    """
    post_dataset
    """
    ds1, ds2, context = test_client

    with context:
        _, code = operations.post_dataset({'invalid': ds1['id']})
        assert code == 400

def test_post_dataset_key_error(test_client):
    """
    post_dataset
    """
    ds1, ds2, context = test_client

    with context:
        _, code = operations.post_dataset({'id': 6547864725, 'version': 55})
        assert code == 500


def test_get_dataset_by_id(test_client):
    """
    get_dataset_by_id
    """

    ds1, ds2, context = test_client

    with context:
        # result, code = operations.get_dataset_by_id(ds1['id'])
        # assert result['id'] == uuid.UUID(ds1['id']).hex
        # assert code == 200

        result, code = operations.get_dataset_by_id(ds2['id'])
        assert result['id'] == uuid.UUID(ds2['id']).hex
        assert code == 200



def test_get_dataset_by_id_key_error(test_client):
    """
    get_dataset_by_id
    """

    ds1, _, context = test_client

    with context:

        result, code = operations.get_dataset_by_id('Wrong')
        assert code == 404


def test_delete_dataset_by_id(test_client):
    """
    delete_dataset_by_id
    """

    _, ds2, context = test_client

    with context:
        _, code = operations.delete_dataset_by_id(ds2['id'])
        assert code == 204

        result, code = operations.get_dataset_by_id(ds2['id'])
        assert code == 404


def test_delete_dataset_by_id_missing(test_client):
    """
    delete_dataset_by_id
    """

    _, ds2, context = test_client

    with context:
        _, code = operations.delete_dataset_by_id(uuid.uuid1().hex)
        assert code == 404


def test_delete_dataset_by_id_bad_UUID(test_client):
    """
    delete_dataset_by_id
    """

    _, ds2, context = test_client

    with context:
        _, code = operations.delete_dataset_by_id('wrong')
        assert code == 500
        _, code = operations.delete_dataset_by_id(564564)
        assert code == 500


def test_search_datasets_basic(test_client):
    """
    search_datasets
    """

    ds1, ds2, context = test_client

    with context:
        result, code = operations.get_dataset_by_id(ds1['id'])
        assert result['id'] == uuid.UUID(ds1['id']).hex
        assert code == 200

        result, code = operations.get_dataset_by_id(ds2['id'])
        assert result['id'] == uuid.UUID(ds2['id']).hex
        assert code == 200

        datasets, code = operations.search_datasets()
        assert len(datasets) == 2
        assert datasets == [ds1, ds2]
        assert code == 200


def load_test_objects():
    dataset_1_id = uuid.uuid4().hex
    dataset_2_id = uuid.uuid4().hex

    test_dataset_1 = {
        'id': dataset_1_id,
        'name': 'dataset_1',
        'description': 'mock profyle project for testing',
        'tags': ['test', 'candig'],
        'version': Version
    }


    test_dataset_2 = {
        'id': dataset_2_id,
        'name': 'dataset_2',
        'description': 'mock tf4cn project for testing',
        'tags': ['test', 'candig'],
        'version': Version
    }

    operations.post_dataset(test_dataset_1)
    operations.post_dataset(test_dataset_2)


    return test_dataset_1, test_dataset_2

