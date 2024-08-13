import pytest
import ckan.model as model
import ckanext.orgportals.db as db

@pytest.fixture
def orgportals_setup():
    db.init()


@pytest.fixture
def clean_orgportals():
    if db.page_table is not None:
        model.Session.query(db.Page).delete()
        model.Session.commit()

    # if db.subdashboard_table is not None:
    #     model.Session.query(db.Subdashboard).delete()
    #     model.Session.commit()
