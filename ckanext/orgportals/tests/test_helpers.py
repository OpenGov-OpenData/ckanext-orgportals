import datetime
import pytest

from nose.tools import assert_raises
try:
    from webob.multidict import MultiDict
except ImportError:
    from webob import UnicodeMultiDict as MultiDict

from ckan import plugins
import ckan.lib.search as search
from ckan.tests import factories
from ckan.plugins import toolkit
from ckan.common import config

from ckanext.orgportals.tests.helpers import (id_generator, create_mock_data)
from ckanext.orgportals import helpers


class BaseTestHelpers(object):
    @pytest.fixture(autouse=True)
    def request_context(self, monkeypatch, ckan_config, app):
        monkeypatch.setitem(ckan_config, "ckan.site_url", "http://example.com")
        self.request_context = app.flask_app.test_request_context()
        self.request_context.push()
        yield
        self.request_context.pop()


@pytest.mark.usefixtures('orgportals_setup')
class TestHelpers(BaseTestHelpers):

    @pytest.fixture(autouse=True)
    def setup(self):
        organization_name = id_generator()
        dataset_name = id_generator()
        group_name = id_generator()
        resource_name = id_generator()
        resource_view_title = id_generator()

        self.mock_data = create_mock_data(
            organization_name=organization_name,
            dataset_name=dataset_name,
            group_name=group_name,
            resource_name=resource_name,
            resource_view_title=resource_view_title)

        # self.subdashboard = create_subdashboard(self.mock_data)

        if toolkit.check_ckan_version(u'2.9'):
            self.controller = 'orgportals_blueprint'
        else:
            self.controller = \
                'ckanext.orgportals.controllers.portals:OrgportalsController'

    def test_get_newly_released_data(self, **kwargs):
        dataset_found = False

        try:
            packages = helpers.orgportals_get_newly_released_data(
                organization_name='',
                subdashboard_group_name=None,
                limit=5)
        except search.SearchError:
            dataset_found = False
            assert not dataset_found

        packages = helpers.orgportals_get_newly_released_data(
            organization_name=self.mock_data['organization_name'],
            subdashboard_group_name=None,
            limit=5)

        assert len(packages) > 0

        for item in packages:
            if item['name'] == self.mock_data['dataset_name']:
                dataset_found = True

        assert dataset_found is True

        # packages = helpers.orgportals_get_newly_released_data(
        #     organization_name=self.mock_data['organization_name'],
        #     subdashboard_group_name=self.mock_data['group_name'],
        #     limit=5)

        # assert len(packages) == 1

        # if packages[0]['name'] == self.mock_data['dataset_name']:
        #     dataset_found = True

        assert dataset_found is True

    def test_convert_time_format(self):
        formatted_date = helpers.orgportals_convert_time_format(
            self.mock_data['dataset'])

        today = datetime.date.today()

        assert formatted_date == today.strftime("%d %B %Y")

    # def test_replace_or_add_url_param(self):
    #     organization_name = self.mock_data['organization_name']
    #     subdashboard_name = self.subdashboard['name']
    #     author = 'John Doe'
    #     controller = self.controller
    #     action = 'show_portal_datapage'
    #     name = 'tags'
    #     value = 'nature'
    #
    #     url = helpers.orgportals_replace_or_add_url_param(
    #         name=name,
    #         value=value,
    #         params=[],
    #         controller=controller,
    #         action=action,
    #         context_name=organization_name,
    #         subdashboard_name=None,
    #         source=None)
    #     assert url == '/data?{0}={1}'.format(name, value)
    #
    #     url = helpers.orgportals_replace_or_add_url_param(
    #         name=name,
    #         value=value,
    #         params=[('page', '2'), ('author', author)],
    #         controller=controller,
    #         action=action,
    #         context_name=organization_name,
    #         subdashboard_name=None,
    #         source=None)
    #     new_url = '/data?author={0}&{1}={2}'\
    #         .format('+'.join(author.split(' ')), name, value)
    #     assert url == new_url
    #
    #     action = 'show_portal_subdashboardpage'
    #     url = helpers.orgportals_replace_or_add_url_param(
    #         name=name,
    #         value=value,
    #         params=[],
    #         controller=controller,
    #         action=action,
    #         context_name=organization_name,
    #         subdashboard_name=subdashboard_name,
    #         source=None)
    #     assert url == '/subdashboard/{0}?{1}={2}'.format(
    #         subdashboard_name, name, value)
    #
    #     action = 'datapage_show'
    #     url = helpers.orgportals_replace_or_add_url_param(
    #         name=name,
    #         value=value,
    #         params=[],
    #         controller=controller,
    #         action=action,
    #         context_name=organization_name,
    #         subdashboard_name=None,
    #         source='admin')
    #     assert url == '/organization/{0}/portal/data?{1}={2}'.format(
    #         organization_name, name, value)
    #
    #     action = 'subdashboardpage_show'
    #     url = helpers.orgportals_replace_or_add_url_param(
    #         name=name,
    #         value=value,
    #         params=[],
    #         controller=controller,
    #         action=action,
    #         context_name=organization_name,
    #         subdashboard_name=subdashboard_name,
    #         source='admin')
    #     assert url == '/organization/{0}/portal/subdashboard/{1}?{2}={3}'.\
    #         format(organization_name, subdashboard_name, name, value)

    def test_get_resourceview_resource_package(self):
        chart_resources = helpers.orgportals_get_resourceview_resource_package(
            self.mock_data['resource_view_id'])

        resource_view = chart_resources[0]
        resource = chart_resources[1]
        package = chart_resources[2]

        assert resource_view['title'] == self.mock_data['resource_view_title']
        assert resource['name'] == self.mock_data['resource_name']
        assert package['name'] == self.mock_data['dataset_name']

    def test_get_all_organizations(self):

        # Create another organization.
        # factories.Organization(name='another_organization')

        organizations = helpers.orgportals_get_all_organizations(
            self.mock_data['organization_name'])

        assert len(organizations) > 0

        assert organizations[0]['text'] == 'None'
        assert organizations[0]['value'] == 'none'

        assert organizations[1]['text'] == ''
        assert organizations[1]['value'] == 'test_org'

    def test_get_available_languages(self):
        languages = helpers.orgportals_get_available_languages()

        assert len(languages) > 0
        language = dict((i['text'], i['value']) for i in languages)
        assert 'English' in language



    def test_get_resource_url(self):
        url = helpers.orgportals_get_resource_url(
            self.mock_data['resource_id'])

        assert url == self.mock_data['resource']['url']

    def test_convert_to_list(self):
        resource_id = self.mock_data['resource_id']
        resources = helpers.orgportals_convert_to_list(resource_id)

        assert len(resources) == 1

        assert resources[0] == resource_id

        resource_ids = self.mock_data['resource_id'] + ';' +\
            self.mock_data['resource_id']
        resources = helpers.orgportals_convert_to_list(resource_ids)

        assert len(resources) == 2

        assert resources[0] == resource_id
        assert resources[1] == resource_id

    def test_get_resource_names_from_ids(self):
        resource_ids = [self.mock_data['resource_id']]
        resource_names = helpers.orgportals_get_resource_names_from_ids(
            resource_ids)

        assert len(resource_names) == 1

        assert resource_names[0] == self.mock_data['resource_name']

    def test_get_secondary_language(self):
        secondary_language = helpers.orgportals_get_secondary_language(
            self.mock_data['organization_name'])

        assert secondary_language == 'none'

        data_dict = {
            'id': self.mock_data['organization_id'],
            'orgportals_secondary_language': 'fr'
        }

        toolkit.get_action('organization_patch')(
            self.mock_data['context'],
            data_dict)

        secondary_language = helpers.orgportals_get_secondary_language(
            self.mock_data['organization_name'])

        assert secondary_language == 'fr'

    # def test_get_current_url(self):
    #     controller = self.controller
    #     name = self.mock_data['organization_name']
    #     page = 5
    #     subdashboard_name = self.subdashboard['name']
    #     organization_name = self.mock_data['organization_name']
    #
    #     action = 'show_portal_datapage'
    #     current_url = helpers.orgportals_get_current_url(
    #         page=page,
    #         params=[],
    #         controller=controller,
    #         action=action,
    #         name=name,
    #         subdashboard_name=None,
    #         source=None,
    #         exclude_param='page')
    #     assert current_url == '/data?page={0}'.format(page)
    #
    #     action = 'show_portal_subdashboardpage'
    #     current_url = helpers.orgportals_get_current_url(
    #         page=page,
    #         params=[],
    #         controller=controller,
    #         action=action,
    #         name=name,
    #         subdashboard_name=subdashboard_name,
    #         source=None,
    #         exclude_param='page')
    #     assert current_url == '/subdashboard/{0}?page={1}'.format(
    #         subdashboard_name, page)
    #
    #     action = 'datapage_show'
    #     current_url = helpers.orgportals_get_current_url(
    #         page=page,
    #         params=[],
    #         controller=controller,
    #         action=action,
    #         name=name,
    #         subdashboard_name=None,
    #         source='admin',
    #         exclude_param='page')
    #     assert current_url == '/organization/{0}/portal/data?page={1}'.format(
    #         organization_name, page)
    #
    #     action = 'subdashboardpage_show'
    #     current_url = helpers.orgportals_get_current_url(
    #         page=page,
    #         params=[],
    #         controller=controller,
    #         action=action,
    #         name=name,
    #         subdashboard_name=subdashboard_name,
    #         source='admin',
    #         exclude_param='page')
    #     assert current_url ==\
    #         '/organization/{0}/portal/subdashboard/{1}?page={2}'.format(
    #             organization_name, subdashboard_name, page)

    def test_get_country_short_name(self):
        country_short_name = helpers.orgportals_get_country_short_name('en')

        assert country_short_name == 'Eng'

        country_short_name = helpers.orgportals_get_country_short_name('fr')

        assert country_short_name == 'Fre'

    def test_orgportals_get_organization_entity_name(self):
        entity_name = helpers.orgportals_get_organization_entity_name()

        assert entity_name == 'organization'

        config['ckanext.orgportals.organization_entity_name'] = 'country'

        entity_name = helpers.orgportals_get_organization_entity_name()

        assert entity_name == 'country'

    def test_orgportals_get_group_entity_name(self):
        entity_name = helpers.orgportals_get_group_entity_name()

        assert entity_name == 'group'

        config['ckanext.orgportals.group_entity_name'] = 'topic'

        entity_name = helpers.orgportals_get_group_entity_name()

        assert entity_name == 'topic'

    def test_orgportals_get_resource_view_url(self):
        id = self.mock_data['resource_id']
        dataset = self.mock_data['dataset_name']

        url = helpers.orgportals_get_resource_view_url(id, dataset)

        assert url == '/dataset/{0}/resource/{1}'.format(dataset, id)

    def test_orgportals_get_copyright_text(self):
        org_name = self.mock_data['organization_name']
        copyright = helpers.orgportals_get_copyright_text(org_name)

        assert copyright == '2016'

    def test_orgportals_get_pages(self):
        org_name = self.mock_data['organization_name']
        pages = helpers.orgportals_get_pages(org_name)

        assert len(pages) > 0

    def test_orgportals_show_exit_button(self):
        params = MultiDict({'author': 'John Doe'})
        show_button = helpers.orgportals_show_exit_button(params)
        assert show_button is False

        params = MultiDict({'q': 'test'})
        show_button = helpers.orgportals_show_exit_button(params)
        assert show_button is True

    # def test_orgportals_is_subdashboard_active(self):
    #     org_name = self.mock_data['organization_name']
    #     subdashboard_name = self.mock_data['group_name']
    #
    #     is_active = helpers.orgportals_is_subdashboard_active(
    #         org_name, subdashboard_name)
    #
    #     assert is_active is True

    def test_orgportals_get_current_organization(self):
        org_name = self.mock_data['organization_name']
        org = helpers.orgportals_get_current_organization(org_name)

        assert org['name'] == org_name

    def test_get_secondary_portal(self):
        secondary_portal = helpers.orgportals_get_secondary_portal(
            self.mock_data['organization_name'])

        assert secondary_portal == 'none'

        data_dict = {
            'id': self.mock_data['organization_id'],
            'orgportals_secondary_portal': 'some_portal'
        }

        toolkit.get_action('organization_patch')(
            self.mock_data['context'],
            data_dict)

        secondary_portal = helpers.orgportals_get_secondary_portal(
            self.mock_data['organization_name'])

        assert secondary_portal == 'some_portal'

    def test_orgportals_get_facebook_app_id(self):
        config['ckanext.orgportals.facebook_app_id'] = 123456
        id = helpers.orgportals_get_facebook_app_id()

        assert id == 123456

    def test_orgportals_get_countries(self):
        countries = helpers.orgportals_get_countries()

        assert len(countries) > 0
        assert {'text': u'Macedonia', 'value': u'Macedonia'} in countries

    def test_orgportals_get_twitter_consumer_keys(self):
        twitter_consumer_key =\
            config['ckanext.orgportals.twitter_consumer_key']
        twitter_consumer_secret =\
            config['ckanext.orgportals.twitter_consumer_secret']

        keys = helpers.orgportals_get_twitter_consumer_keys()
        twitter_keys = {
            'twitter_consumer_key': twitter_consumer_key,
            'twitter_consumer_secret': twitter_consumer_secret
        }

        assert keys['twitter_consumer_key'] ==\
            twitter_keys['twitter_consumer_key']
        assert keys['twitter_consumer_secret'] ==\
            twitter_keys['twitter_consumer_secret']

    def test_orgportals_get_organization_image(self):
        org_name = self.mock_data['organization_name']
        image = helpers.orgportals_get_organization_image(org_name)

        assert image == self.mock_data['organization_image']
