import datetime
import json
import base64
import os
import logging

import twitter
from ckan.plugins.toolkit import config
# from selenium import webdriver

import ckan.plugins as p
import ckan.lib.navl.dictization_functions as df
from ckan.plugins import toolkit as tk
import ckan.logic.action.create as create_core
import ckan.logic.action.update as update_core
from ckan import model

from ckanext.orgportals import db, helpers

try:
    unicode_safe = tk.get_validator('unicode_safe')
except tk.UnknownValidator:
    # CKAN 2.7
    unicode_safe = unicode # noqa: F821

log = logging.getLogger(__name__)

def organization_create(context, data_dict):
    try:
        data_dict.update({'orgportals_portal_created': u'1'})
        org = create_core.organization_create(context, data_dict)
        _create_portal(data_dict['name'])

        return org
    except p.toolkit.ValidationError:
        return create_core.organization_create(context, data_dict)


def organization_update(context, data_dict):
    try:
        org_show = tk.get_action('organization_show')({}, {'id': data_dict['name']})

        if 'orgportals_portal_created' not in org_show:
            _create_portal(data_dict['name'])

        data_dict.update({'orgportals_portal_created': u'1'})
        org = update_core.organization_update(context, data_dict)

        return org
    except p.toolkit.ValidationError:
        return update_core.organization_update(context, data_dict)


def page_name_validator(key, data, errors, context):
    session = context['session']
    page_name = context.get('page_name')
    org_name = context.get('org_name')

    if page_name and page_name == data[key]:
        return

    query = session.query(db.Page.name).filter_by(name=data[key], org_name=org_name)

    result = query.first()

    if result:
        errors[key].append(
            p.toolkit._('This page name already exists. Choose another one.'))

def subdashboard_name_validator(key, data, errors, context):
    session = context['session']
    name = context.get('subdashboard_name')
    org_name = context.get('org_name')

    if name and name == data[key]:
        return

    query = session.query(db.Subdashboard.name).filter_by(name=data[key], org_name=org_name)

    result = query.first()

    if result:
        errors[key].append(
            p.toolkit._('This subdashboard name already exists. Choose another one.'))

pages_schema = {
    'id': [p.toolkit.get_validator('ignore_empty'), unicode_safe],
    'name': [p.toolkit.get_validator('not_empty'), unicode_safe,
             p.toolkit.get_validator('name_validator'), page_name_validator],
    'org_name': [p.toolkit.get_validator('not_empty'), unicode_safe],
    'type': [p.toolkit.get_validator('not_empty'), unicode_safe],
    'page_title': [p.toolkit.get_validator('not_empty'), unicode_safe],
    'content_title': [p.toolkit.get_validator('ignore_missing'), unicode_safe],
    'order': [p.toolkit.get_validator('ignore_missing'), unicode_safe],
    'image_url': [p.toolkit.get_validator('ignore_empty'), unicode_safe],
    'image_url_2': [p.toolkit.get_validator('ignore_empty'), unicode_safe],
    'image_url_3': [p.toolkit.get_validator('ignore_empty'), unicode_safe],
    'text_box': [p.toolkit.get_validator('ignore_empty'), unicode_safe],
    'content': [p.toolkit.get_validator('ignore_missing'), unicode_safe],
    'topics': [p.toolkit.get_validator('ignore_missing'), unicode_safe],
    'datasets_per_page': [p.toolkit.get_validator('ignore_empty'), int],
    'survey_enabled': [p.toolkit.get_validator('ignore_missing'),
                       p.toolkit.get_validator('boolean_validator')],
    'survey_text': [p.toolkit.get_validator('ignore_missing'), unicode_safe],
    'survey_link': [p.toolkit.get_validator('ignore_missing'), unicode_safe],
    'map': [p.toolkit.get_validator('ignore_missing'), unicode_safe],
    'map_main_property': [p.toolkit.get_validator('ignore_missing'), unicode_safe],
    'map_enabled': [p.toolkit.get_validator('ignore_missing'),
                    p.toolkit.get_validator('boolean_validator')],
    'created': [p.toolkit.get_validator('ignore_missing'),
                p.toolkit.get_validator('isodate')],
    'updated': [p.toolkit.get_validator('ignore_missing'),
                p.toolkit.get_validator('isodate')]
}

subdashboards_schema = {
    'id': [p.toolkit.get_validator('ignore_empty'), unicode_safe],
    'name': [p.toolkit.get_validator('not_empty'), unicode_safe,
             p.toolkit.get_validator('name_validator'), subdashboard_name_validator],
    'org_name': [p.toolkit.get_validator('not_empty'), unicode_safe],
    'group': [p.toolkit.get_validator('not_empty'), unicode_safe],
    'is_active': [p.toolkit.get_validator('not_empty'),
                  p.toolkit.get_validator('boolean_validator')],
    'subdashboard_description': [p.toolkit.get_validator('ignore_empty'), unicode_safe],
    'icon_description': [p.toolkit.get_validator('ignore_empty'), unicode_safe],
    'map': [p.toolkit.get_validator('ignore_missing'), unicode_safe],
    'map_main_property': [p.toolkit.get_validator('ignore_missing'), unicode_safe],
    'map_enabled': [p.toolkit.get_validator('ignore_missing'),
                    p.toolkit.get_validator('boolean_validator')],
    'data_section_enabled': [p.toolkit.get_validator('not_empty'),
                             p.toolkit.get_validator('boolean_validator')],
    'content_section_enabled': [p.toolkit.get_validator('not_empty'),
                                p.toolkit.get_validator('boolean_validator')],
    'media': [p.toolkit.get_validator('ignore_missing'), unicode_safe],
    'created': [p.toolkit.get_validator('ignore_missing'),
                p.toolkit.get_validator('isodate')],
    'updated': [p.toolkit.get_validator('ignore_missing'),
                p.toolkit.get_validator('isodate')]
}

def _pages_show(context, data_dict):
    org_name = data_dict['org_name']
    page_name = data_dict['page_name']
    page = db.Page.get_page_for_org(org_name, page_name)
    if page:
        page = db.table_dictize(page, context)
    return page

def _pages_list(context, data_dict):
    org_name = data_dict['org_name']
    pages = db.Page.get_pages_for_org(org_name=org_name)
    pages_dictized = []

    for page in pages:
        page = db.table_dictize(page, context)
        pages_dictized.append(page)

    return pages_dictized

def _pages_delete(context, data_dict):
    org_name = data_dict['org_name']
    page_name = data_dict['page_name']
    page = db.Page.get_page_for_org(org_name, page_name)
    if page:
        session = context['session']
        session.delete(page)
        session.commit()

def _pages_update(context, data_dict):

    org_name = data_dict.get('org_name')
    _page_name = data_dict.get('page_name')
    page_name = data_dict.get('name')
    page_title = data_dict.get('page_title')
    # we need the page in the context for name validation
    context['page_name'] = _page_name
    context['org_name'] = org_name

    session = context['session']

    data, errors = df.validate(data_dict, pages_schema, context)

    if errors:
        raise p.toolkit.ValidationError(errors)

    out = db.Page.get_page_for_org(org_name, _page_name)

    if not out:
        out = db.Page()
        out.org_name = org_name
        out.name = page_name

    items = ['page_title', 'content_title', 'content', 'name', 'image_url', 'image_url_2', 'image_url_3',
             'type', 'text_box',
             'topics', 'datasets_per_page', 'survey_enabled',
             'survey_text', 'survey_link', 'map', 'map_main_property',
             'map_enabled', 'order']
    for item in items:
        setattr(out, item, data.get(item))

    extras = {}
    extra_keys = set(pages_schema.keys()) - set(items + ['id', 'created'])
    for key in extra_keys:
        if key in data:
            extras[key] = data.get(key)
    out.extras = json.dumps(extras)

    out.modified = datetime.datetime.utcnow()
    out.save()
    session.add(out)
    session.commit()

def _subdadashboards_list(context, data_dict):
    org_name = data_dict['org_name']
    subdashboards = db.Subdashboard.get_subdashboards_for_org(org_name=org_name)
    subdashboards_dictized = []

    for subdashboard in subdashboards:
        subdashboard = db.table_dictize(subdashboard, context)
        subdashboards_dictized.append(subdashboard)

    return subdashboards_dictized

def _subdashboards_show(context, data_dict):
    org_name = data_dict['org_name']
    subdashboard_name = data_dict['subdashboard_name']
    subdashboard = db.Subdashboard.get_subdashboard_for_org(org_name, subdashboard_name)
    if subdashboard:
        subdashboard = db.table_dictize(subdashboard, context)
    return subdashboard

def _subdashboards_update(context, data_dict):

    org_name = data_dict.get('org_name')
    subdashboard_name = data_dict.get('subdashboard_name')
    name = data_dict.get('name')
    # we need the subdashboard in the context for name validation
    context['subdashboard_name'] = subdashboard_name
    context['org_name'] = org_name

    session = context['session']

    data, errors = df.validate(data_dict, subdashboards_schema, context)

    if errors:
        raise p.toolkit.ValidationError(errors)

    out = db.Subdashboard.get_subdashboard_for_org(org_name, subdashboard_name)

    if not out:
        out = db.Subdashboard()
        out.name = name

    items = [
        'name',
        'org_name',
        'group',
        'is_active',
        'subdashboard_description',
        'icon_description',
        'map',
        'map_main_property',
        'map_enabled',
        'data_section_enabled',
        'content_section_enabled',
        'media',
    ]

    for item in items:
        setattr(out, item, data.get(item))

    extras = {}
    extra_keys = set(subdashboards_schema.keys()) - set(items + ['id', 'created'])
    for key in extra_keys:
        if key in data:
            extras[key] = data.get(key)
    out.extras = json.dumps(extras)

    out.modified = datetime.datetime.utcnow()
    out.save()
    session.add(out)
    session.commit()

def _subdashboards_delete(context, data_dict):
    org_name = data_dict['org_name']
    subdashboard_name = data_dict['subdashboard_name']
    subdashboard = db.Subdashboard.get_subdashboard_for_org(org_name, subdashboard_name)

    if subdashboard:
        session = context['session']
        session.delete(subdashboard)
        session.commit()


def _create_portal(org_name):
    _create_pages(org_name)


def _create_pages(org_name):
    pages = [
        {'org_name': org_name, 'type': 'home', 'name': 'home', 'page_title': 'Home', 'order': 0},
        {'org_name': org_name, 'type': 'data', 'name': 'data', 'page_title': 'Data', 'order': 1},
        {'org_name': org_name, 'type': 'library', 'name': 'library', 'page_title': 'Document Library', 'order': 2},
        {'org_name': org_name, 'type': 'default', 'name': 'about', 'page_title': 'About', 'order': 3}
    ]

    for page in pages:
        out = db.Page()
        out.name = page['name']
        out.org_name = page['org_name']
        out.type = page['type']
        out.page_title = page['page_title']
        out.order = page['order']
        out.save()
        model.Session.add(out)

    model.Session.commit()


@tk.side_effect_free
def pages_show(context, data_dict):
    try:
        p.toolkit.check_access('orgportals_pages_show', context, data_dict)
    except p.toolkit.NotAuthorized:
        p.toolkit.abort(401, p.toolkit._('Not authorized to see this page'))
    return _pages_show(context, data_dict)


def pages_update(context, data_dict):
    try:
        p.toolkit.check_access('orgportals_pages_update', context, data_dict)
    except p.toolkit.NotAuthorized:
        p.toolkit.abort(401, p.toolkit._('Not authorized to see this page'))
    return _pages_update(context, data_dict)


def pages_delete(context, data_dict):
    try:
        p.toolkit.check_access('orgportals_pages_delete', context, data_dict)
    except p.toolkit.NotAuthorized:
        p.toolkit.abort(401, p.toolkit._('Not authorized to see this page'))
    return _pages_delete(context, data_dict)

@tk.side_effect_free
def pages_list(context, data_dict):
    return _pages_list(context, data_dict)

@p.toolkit.side_effect_free
def orgportals_resource_show_map_properties(context, data_dict):
    return helpers.orgportals_get_geojson_properties(data_dict.get('id'))

@tk.side_effect_free
def subdashboards_list(context, data_dict):
    return _subdadashboards_list(context, data_dict)

@tk.side_effect_free
def subdashboards_show(context, data_dict):
    try:
        p.toolkit.check_access('orgportals_subdashboards_show', context, data_dict)
    except p.toolkit.NotAuthorized:
        p.toolkit.abort(401, p.toolkit._('Not authorized to see this subdashboard'))
    return _subdashboards_show(context, data_dict)

def subdashboards_update(context, data_dict):
    try:
        p.toolkit.check_access('orgportals_subdashboards_update', context, data_dict)
    except p.toolkit.NotAuthorized:
        p.toolkit.abort(401, p.toolkit._('Not authorized to see this subdashboard'))
    return _subdashboards_update(context, data_dict)

def subdashboards_delete(context, data_dict):
    try:
        p.toolkit.check_access('orgportals_subdashboards_delete', context, data_dict)
    except p.toolkit.NotAuthorized:
        p.toolkit.abort(401, p.toolkit._('Not authorized to see this subdashboard'))
    return _subdashboards_delete(context, data_dict)


@p.toolkit.side_effect_free
def orgportals_show_datasets(context, data_dict):
    dd = data_dict.copy()
    dd.update({'include_datasets': True})

    data = helpers._get_action('organization_show', context.copy(), dd)
    return data.pop('packages', [])


@p.toolkit.side_effect_free
def orgportals_dataset_show_resources(context, data_dict):
    data = helpers._get_action('package_show', context.copy(), data_dict)

    return data.pop('resources', [])


@p.toolkit.side_effect_free
def orgportals_resource_show_resource_views(context, data_dict):
    data = helpers._get_action('resource_view_list', context.copy(), data_dict)
    data = filter(lambda i: i['view_type'] == data_dict['view_type'], data)
    data = list(data)

    return data

def orgportals_share_graph_on_twitter(context, data_dict):
    access_token_key = data_dict['oauth_token']
    access_token_secret = data_dict['oauth_token_secret']
    image = data_dict['image']
    graph_title = data_dict['graph_title']
    subdashboard_url = data_dict['subdashboard_url']

    twitter_keys = helpers.orgportals_get_twitter_consumer_keys()

    try:
        api = twitter.Api(consumer_key=twitter_keys['twitter_consumer_key'],
                          consumer_secret=twitter_keys['twitter_consumer_secret'],
                          access_token_key=access_token_key,
                          access_token_secret=access_token_secret)

        image_data = base64.b64decode(image)
        fallback_storage_path = os.path.dirname(os.path.realpath(__file__))
        file = '{0}/{1}'.format(config.get('ckan.storage_path', fallback_storage_path), 'graph_image.png')

        with open(file, 'wb') as f:
            f.write(image_data)

        api.PostUpdate('{0} {1}'.format(graph_title, subdashboard_url), media=file)

        os.remove(file)
    except Exception as e:
        log.error(e)

        return {'share_status_success': False}

    return {'share_status_success': True}


def orgportals_share_link_on_twitter(context, data_dict):
    access_token_key = data_dict['oauth_token']
    access_token_secret = data_dict['oauth_token_secret']
    url = data_dict['url']
    title = data_dict['title']
    subdashboard_url = data_dict['subdashboard_url']
    url_type = data_dict['url_type']

    twitter_keys = helpers.orgportals_get_twitter_consumer_keys()

    try:
        api = twitter.Api(consumer_key=twitter_keys['twitter_consumer_key'],
                          consumer_secret=twitter_keys['twitter_consumer_secret'],
                          access_token_key=access_token_key,
                          access_token_secret=access_token_secret)

        if url_type == 'image':
            api.PostUpdate('{0} {1}'.format(title, subdashboard_url), media=url)
        elif url_type == 'video':
            api.PostUpdate('{0} {1} {2}'.format(title, subdashboard_url, url))

    except Exception as e:
        log.error(e)

        return {'share_status_success': False}

    return {'share_status_success': True}



# @p.toolkit.side_effect_free
# def orgportals_download_dashboard(context, data_dict):
#     try:
#         url = data_dict['url']
#     except KeyError:
#         return {
#             'error': 'Missing parameter: url'
#         }
#
#     try:
#         fallback_storage_path = os.path.dirname(os.path.realpath(__file__))
#         log_path = '{0}/phantomjs.log'.format(config.get('ckan.storage_path',
#                                               fallback_storage_path))
#         driver = webdriver.PhantomJS(service_log_path=log_path)
#         image = '{0}/montrose-dashboard.png'.format(
#             config.get('ckan.storage_path', fallback_storage_path))
#
#         driver.set_window_size(1320, 1080)
#         driver.get(url)
#         driver.save_screenshot(image)
#
#         os.remove(image)
#
#         image_data = driver.get_screenshot_as_base64()
#
#         return {
#             'image_data': image_data
#         }
#     except Exception as e:
#         log.error(e)
#
#         return {
#             'error': 'Cannot create snapshot'
#         }
