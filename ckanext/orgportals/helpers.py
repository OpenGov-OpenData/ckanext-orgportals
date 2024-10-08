import logging
from datetime import datetime
from six import string_types
from six.moves.urllib.parse import urlencode
from six.moves.urllib.parse import urlsplit, urlunsplit
import os
import requests
import six
from operator import itemgetter
try:
    from collections import OrderedDict
except ImportError:
    from sqlalchemy.util import OrderedDict

from ckan.plugins import toolkit
from ckan.plugins.toolkit import config
from ckan.lib import search
import ckan.lib.helpers as lib_helpers
import ckan.lib.i18n as i18n
from ckan import model
from ckan.common import json, request
import ckan.logic as l

log = logging.getLogger(__name__)

MAX_FILE_SIZE = 1024 * 1024 * 50  # 50 Mb
CHUNK_SIZE = 1024


def _get_ctx():
    return {
        'model': model,
        'session': model.Session,
        'user': 'sysadmin'
    }


def _get_action(action, context_dict, data_dict):
    return toolkit.get_action(action)(context_dict, data_dict)


def orgportals_get_newly_released_data(organization_name, subdashboard_group_name, limit=4):
    if subdashboard_group_name:
        fq = 'organization:"{0}"+groups:"{1}"'.format(organization_name, subdashboard_group_name)
    else:
        fq = 'organization:{}'.format(organization_name)

    try:
        pkg_search_results = toolkit.get_action('package_search')(data_dict={
            'fq': fq,
            'sort': 'metadata_modified desc',
            'rows': limit
        })['results']

    except (toolkit.ValidationError, search.SearchError):
        return []
    else:
        pkgs = []

        for pkg in pkg_search_results:
            package = toolkit.get_action('package_show')(data_dict={
                'id': pkg['id']
            })
            modified = datetime.strptime(
                package['metadata_modified'].split('T')[0], '%Y-%m-%d')
            package['human_metadata_modified'] = modified.strftime("%d %B %Y")
            pkgs.append(package)

        return pkgs


def orgportals_convert_time_format(package):
    modified = datetime.strptime(
        package['metadata_modified'].split('T')[0], '%Y-%m-%d')

    return modified.strftime("%d %B %Y")


def orgportals_get_resource_view_url(id, dataset):
    return '/dataset/{0}/resource/{1}'.format(dataset, id)


def orgportals_get_group_entity_name():
    return config.get('ckanext.orgportals.group_entity_name', 'group')


def orgportals_get_organization_entity_name():
    return config.get('ckanext.orgportals.organization_entity_name', 'organization')


def orgportals_get_facet_items_dict(value):
    try:
        return lib_helpers.get_facet_items_dict(value)
    except:
        return None


def orgportals_replace_or_add_url_param(name, value, params, controller, action,
                                        context_name, subdashboard_name, source):
    params_nopage = [
        (k, v) for k, v in params
        if k != 'page'
    ]

    params_nopage.append((name, value))

    if subdashboard_name:
        if source and source == 'admin':
            url = lib_helpers.url_for(controller=controller,
                                      action=action,
                                      org_name=context_name,
                                      subdashboard_name=subdashboard_name,
                                      source='admin')
        else:
            url = lib_helpers.url_for(controller=controller,
                                      action=action,
                                      subdashboard_name=subdashboard_name)
    else:
        if source and source == 'admin':
            url = lib_helpers.url_for(controller=controller,
                                      action=action,
                                      org_name=context_name,
                                      source='admin')
        else:
            url = lib_helpers.url_for(controller=controller,
                                      action=action)

    params = [(k, v.encode('utf-8') if isinstance(v, string_types) else str(v))
              for k, v in params_nopage]

    return url + u'?' + urlencode(params)


def orgportals_get_current_url(page, params, controller, action, name, subdashboard_name, source,
                               exclude_param=''):
    if subdashboard_name:
        if source and source == 'admin':
            url = lib_helpers.url_for(controller=controller,
                                      action=action,
                                      org_name=name,
                                      subdashboard_name=subdashboard_name,
                                      source='admin')
        else:
            url = lib_helpers.url_for(controller=controller,
                                      action=action,
                                      subdashboard_name=subdashboard_name)
    else:
        if source and source == 'admin':
            url = lib_helpers.url_for(controller=controller,
                                      action=action,
                                      org_name=name,
                                      source='admin')
        else:
            url = lib_helpers.url_for(controller=controller,
                                      action=action)

    params_items = [
        (k, v) for k, v in params
        if k != exclude_param
    ]

    params_items = [(k, v.encode('utf-8') if isinstance(v, string_types) else str(v))
              for k, v in params_items]

    if (params_items):
        url = url + u'?page=' + str(page) + '&' + urlencode(params_items)
    else:
        url = url + u'?page=' + str(page)

    return url


def orgportals_get_copyright_text(organization_name):
    data_dict = {
        'id': organization_name,
        'include_extras': True
    }
    organization = toolkit.get_action('organization_show')(data_dict=data_dict)

    return organization['orgportals_copyright']


def orgportals_convert_to_list(resources):
    if ';' not in resources:
        return [resources]

    resources = resources.split(';')

    return resources


def orgportals_get_resource_url(id):
    try:
        data = toolkit.get_action('resource_show')({}, {'id': id})
    except toolkit.ValidationError:
        return None
    except (toolkit.ObjectNotFound, toolkit.NotAuthorized):
        return None

    return data['url']


def orgportals_get_resource_names_from_ids(resource_ids):
    resource_names = []

    for resource_id in resource_ids:
        resource_names.append(toolkit.get_action('resource_show')({},
                                                 {'id': resource_id})['name'])

    return resource_names


def orgportals_get_org_map_views(name):
        allMaps = {}
        result = [{'value': '', 'text': 'None'}]
        for item in _get_organization_views(name, type='Maps'):
            data = {
                'value': item['id'],
                'text': 'UNNAMED' if item['name'] == '' else item['name']
            }
            result.append(data)
            allMaps.update({name: result})

        return allMaps.get(name) or {}


def _get_organization_views(name, type='chart builder'):
    data_dict = {
        'id': name,
        'include_datasets': True
    }
    data = toolkit.get_action('organization_show')({}, data_dict)

    result = []
    package_names = data.pop('packages', [])

    if any(package_names):
        for _ in package_names:
            package = toolkit.get_action('package_show')({}, {'id': _['name']})
            if not package['num_resources'] > 0:
                continue

            if type == 'chart builder':
                resource_views = map(lambda p: toolkit.get_action('resource_view_list')({},
                                                          {'id': p['id']}), package['resources'])
                if any(resource_views):
                    map(lambda l: result.extend(filter(lambda i: i['view_type'].lower() == type, l)), resource_views)

            elif type.lower() == 'maps':
                result.extend(filter(lambda r: r['format'].lower() in ['geojson', 'gjson'], package['resources']))

            else:
                pass
            # Raise not handled exception

    return result


def orgportals_resource_show_map_properties(id):
    return orgportals_get_geojson_properties(id)


def orgportals_get_geojson_properties(resource_id):
    url = orgportals_get_resource_url(resource_id)
    if not url:
        return []

    length = 0
    content = '' if six.PY2 else b''

    try:
        r = requests.get(url)
        for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
            content = content + chunk

            length += len(chunk)

            if length >= MAX_FILE_SIZE:
                return []
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        log.error("Error getting content from geojson url %s" % url)

    result = []

    try:
        if not six.PY2:
            content = content.decode('utf-8')

        geojson = json.loads(content)

        exclude_keys = [
            'marker-symbol',
            'marker-color',
            'marker-size',
            'stroke',
            'stroke-width',
            'stroke-opacity',
            'fill',
            'fill-opacity'
        ]

        for k, v in geojson.get('features', [])[0].get('properties', {}).iteritems():
            if k not in exclude_keys:
                result.append({'value':k, 'text': k})
    except (ValueError, TypeError, json.JSONDecodeError):
        log.error("Error getting geojson properties")

    return result


def orgportals_get_pages(org_name):
    data_dict = {'org_name': org_name}

    return toolkit.get_action('orgportals_pages_list')({}, data_dict)


def orgportals_get_resourceview_resource_package(resource_view_id):
    if not resource_view_id:
        return None

    data_dict = {
        'id': resource_view_id
    }
    try:
        resource_view = toolkit.get_action('resource_view_show')({}, data_dict)

    except l.NotFound:
        return None

    data_dict = {
        'id': resource_view['resource_id']
    }
    resource = toolkit.get_action('resource_show')({}, data_dict)

    data_dict = {
        'id': resource['package_id']
    }

    try:
        package = toolkit.get_action('package_show')({}, data_dict)

    except l.NotFound:
        return None

    return [resource_view, resource, package]


def orgportals_show_exit_button(params):
    for item in params.items():
        if item[0] == 'q':
            return True

    return False


def orgportals_is_subdashboard_active(org_name, subdashboard_name):
    data_dict = {
        'org_name': org_name,
        'subdashboard_name': subdashboard_name
    }

    subdashboard = toolkit.get_action('orgportals_subdashboards_show')({}, data_dict)

    return subdashboard['is_active']


def orgportals_get_all_organizations(current_org_name):
    ''' Get all created organizations '''

    organizations = _get_action('organization_list', {}, {'all_fields': True})

    organizations = map(lambda item:
                        {
                            'value': item['name'],
                            'text': item['title']
                        },
                        organizations
                    )

    # Filter out the current organization in the list
    organizations = [x for x in organizations if x['value'] != current_org_name]

    organizations.insert(0, {'value': 'none', 'text': 'None'})

    return organizations


def orgportals_get_available_languages():
    languages = []
    locales = []

    if toolkit.check_ckan_version(min_version='2.5.0', max_version='2.5.3'):
        locales = lib_helpers.get_available_locales()
    else:
        locales = i18n.get_available_locales()

    for locale in locales:
        languages.append({'value': locale, 'text': locale.english_name})

    languages.insert(0, {'value': 'none', 'text': 'None'})

    return languages


def orgportals_get_current_organization(org_name):
    data_dict = {
        'id': org_name,
    }

    organization = toolkit.get_action('organization_show')(data_dict=data_dict)

    return organization


def orgportals_get_secondary_portal(organization_name):
    organization = _get_action('organization_show', {}, {'id': organization_name})

    if 'orgportals_secondary_portal' in organization:
        return organization['orgportals_secondary_portal']
    else:
        return 'none'


def orgportals_get_secondary_language(organization_name):
    organization = _get_action('organization_show', {}, {'id': organization_name})

    if 'orgportals_secondary_language' in organization:
        return organization['orgportals_secondary_language']
    else:
        return 'none'


def orgportals_get_country_short_name(current_locale):
    locales = []

    if toolkit.check_ckan_version(min_version='2.5.0', max_version='2.5.3'):
        locales = lib_helpers.get_available_locales()
    else:
        locales = i18n.get_available_locales()

    for locale in locales:
        if current_locale == str(locale):
            return locale.english_name[:3]


def orgportals_get_facebook_app_id():
    return config.get('ckanext.orgportals.facebook_app_id', '')


def orgportals_get_countries():
    countries_path = os.path.join(os.path.dirname(__file__), 'public', 'countries.json')
    if not os.path.isfile(countries_path):
        log.warning("Could not find %s", countries_path)

    result = []
    with open(countries_path, 'r') as countries_json:
        countries = json.load(countries_json, object_pairs_hook=OrderedDict)

        for item in countries.get('features', []):
            result.append({'value': item['properties']['name'], 'text': item['properties']['name']})

        result.sort(key=itemgetter('text'))
        result.insert(0, {'value': 'none', 'text': 'None'})

    return result


def orgportals_get_twitter_consumer_keys():
    twitter_consumer_key = config.get('ckanext.orgportals.twitter_consumer_key', '')
    twitter_consumer_secret = config.get('ckanext.orgportals.twitter_consumer_secret', '')

    return {
        'twitter_consumer_key': twitter_consumer_key,
        'twitter_consumer_secret': twitter_consumer_secret
    }


def orgportals_get_portal_page_url(org_name, current_locale):

    org = _get_action('organization_show', {}, {'id': org_name})

    if 'orgportals_portal_url' in org and org['orgportals_portal_url'] != '':

        new_base_url = urlsplit(org['orgportals_portal_url'])

        request_url = urlsplit(toolkit.request.url)

        tmp_url = list(request_url)
        tmp_url[0] = new_base_url.scheme
        tmp_url[1] = new_base_url.netloc
        tmp_url[2] = '/'+ current_locale + request_url.path
        url = urlunsplit(tmp_url)

        return url
    else:
        return ''


def orgportals_get_organization_image(org_name):
    org = toolkit.get_action('organization_show')({}, {'id': org_name})

    return org['image_display_url']


def orgportals_get_dataset_count(org_name):
    count = 0
    try:
        result = toolkit.get_action('organization_list')({}, {'all_fields':'true', 'limit':1, 'organizations':[org_name]})
        if result[0].get('package_count'):
            count = result[0].get('package_count')
    except:
        pass
    return count


def recent_datasets(org_name, num=5):
    """Return a list of recent datasets."""
    datasets = []
    try:
        search = toolkit.get_action('package_search')({},{'rows': num, 'sort': 'metadata_modified desc', 'fq': 'organization:'+org_name})
        if search.get('results'):
            datasets = search.get('results')
    except:
        pass
    return datasets[:num]


def popular_datasets(org_name, num=5):
    """Return a list of popular datasets."""
    datasets = []
    search = toolkit.get_action('package_search')({},{'rows': num, 'sort': 'views_recent desc', 'fq': 'organization:'+org_name})
    if search.get('results'):
        datasets = search.get('results')
    return datasets[:num]


def get_package_metadata(package):
    """Return the metadata of a dataset"""
    result = {}
    try:
        result = toolkit.get_action('package_show')(None, {'id': package.get('name'), 'include_tracking': True})
    except Exception:
        log.exception("Error in retrieving dataset metadata for %s", package)
        package_metadata = package
        package_metadata['tracking_summary'] = {
            'total': 0,
            'recent': 0
        }
        return package_metadata
    return result


def get_group_list(org_name, num=12):
    """Return a list of groups"""
    org_groups = []
    result = toolkit.get_action('package_search')({}, {'fq':'organization:\"'+org_name+'\"', 'facet.field': ["groups"], 'rows': 0})
    facet_list = result.get('search_facets',{}).get('groups',{}).get('items')
    for item in facet_list:
        group = toolkit.get_action('group_show')({},{'id': item['name'], 'include_users': False})
        if group:
            org_groups.append(group)
    return org_groups[:num]


def get_showcase_list(org_name, num=24):
    """Return a list of showcases"""
    org_showcases = []
    sorted_showcases = []
    try:
        showcase_ids_list = toolkit.get_action('ckanext_organization_showcase_list')({},{'organization_id':org_name})
        if showcase_ids_list:
            for showcase_id in showcase_ids_list:
                showcase = toolkit.get_action('ckanext_showcase_show')({},{'id':showcase_id})
                org_showcases.append(showcase)
        sorted_showcases = sorted(org_showcases, key=lambda k: k.get('metadata_modified'), reverse=True)
    except:
        log.debug("[orgportals] Error in retrieving list of showcases")
    return sorted_showcases[:num]


def get_default_resource_view(resource_id):
    """Return the first resource view"""
    resource_view = ''
    try:
        resource_views = toolkit.get_action('resource_view_list')({},{'id': resource_id})
        if len(resource_views) > 0:
            resource_view = resource_views[0]
    except:
        log.debug("[orgportals] Error in retrieving resource view")
    return resource_view


def search_document_page_exists(page_id):
    try:
        if not page_id:
            return False
        search_doc = toolkit.get_action('ckanext_pages_show')({},{'page': page_id})
        if search_doc.get('content') and not search_doc.get('private'):
            return True
    except:
        log.debug("[orgportals] Error in retrieving page")
    return False
