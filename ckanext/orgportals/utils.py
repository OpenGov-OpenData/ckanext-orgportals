import logging
from six import string_types
from six.moves.urllib.parse import urlencode, urlparse
import cgi
import json
from operator import itemgetter
import requests

import ckan.model as model
from collections import OrderedDict
from ckan.common import _, request, c, g
import ckan.lib.base as base
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.plugins as p
import ckan.plugins.toolkit as tk

import ckan.lib.helpers as h
from ckan.lib.plugins import lookup_package_plugin
from ckan.lib.search import SearchError
import ckan.lib.maintain as maintain
import ckan.lib.uploader as uploader

from ckanext.orgportals import emailer


log = logging.getLogger(__name__)

check_access = logic.check_access
get_action = logic.get_action

ckan_29_or_higher = tk.check_ckan_version(min_version='2.9.0')


def _encode_params(params):
    return [(k, v.encode('utf-8') if isinstance(v, string_types) else str(v))
            for k, v in params]


def url_with_params(url, params):
    params = _encode_params(params)
    return url + u'?' + urlencode(params)


def search_url(params, package_type=None):
    if not package_type:
        package_type == 'dataset'
    if ckan_29_or_higher:
        url = h.url_for(u'{0}.search'.format(package_type))
    else:
        url = h.url_for('{0}_search'.format(package_type))
    return url_with_params(url, params)


def _setup_template_variables(context, data_dict, package_type=None):
    return lookup_package_plugin(package_type).setup_template_variables(
        context, data_dict
    )


def _get_form_data(request):
    if ckan_29_or_higher:
        form_data = _get_flat_dict(request.form)
        form_data.update(_get_flat_dict(request.files))
    else:
        form_data = _get_flat_dict(request.POST)
    return form_data


def _get_flat_dict(data):
    data_dict = logic.clean_dict(
        dict_fns.unflatten(
            logic.tuplize_dict(
                logic.parse_params(data)
            )
        )
    )
    return data_dict


def _upload_image_for_portal(data, field_url, image_upload, clear_upload):
    try:
        upload = uploader.get_uploader('portal', data.get(field_url))
    except AttributeError:
        upload = uploader.Upload('portal', data.get(field_url))

    upload.update_data_dict(data, field_url, image_upload, clear_upload)
    upload.upload(uploader.get_max_image_size())
    return data


def _get_group_dict(org_name):
    context = {
        'model': model, 'session': model.Session,
        'user': c.user or c.author,
    }
    data_dict = {
        'id': org_name,
        'include_datasets': False,
        'include_extras': True
    }
    try:
        group_dict = get_action('organization_show')(context, data_dict)
    except p.toolkit.NotAuthorized:
        p.toolkit.abort(401, _('Unauthorized to see organization'))
    except p.toolkit.ObjectNotFound:
        p.toolkit.abort(404, _('Group not found'))
    return group_dict


def orgportals_pages_index(org_name):
    data_dict = {'org_name': org_name}
    pages = get_action('orgportals_pages_list')({}, data_dict)
    c.pages = pages

    group_dict = _get_group_dict(org_name)
    c.group_dict = group_dict

    extra_vars = {
        'pages': pages,
        'group_dict': group_dict,
        'group_type': 'organization'
    }

    return p.toolkit.render('organization/pages_list.html', extra_vars=extra_vars)


def orgportals_pages_edit(org_name, page=None, data=None, errors=None, error_summary=None):
    data_dict = {
        'org_name': org_name,
        'page_name': page
    }
    _page = get_action('orgportals_pages_show')({}, data_dict)

    if _page is None and len(page) > 0:
        p.toolkit.abort(404, _('Page not found.'))

    if _page is None:
        _page = {}

    if p.toolkit.request.method == 'POST' and not data:
        if 'type' not in _page:
            _page['type'] = 'custom'

        data = _get_form_data(tk.request)

        # Upload images for portal pages
        _upload_image_for_portal(data, 'image_url', 'image_upload', 'clear_upload')
        _upload_image_for_portal(data, 'image_url_2', 'image_upload_2', 'clear_upload_2')
        _upload_image_for_portal(data, 'image_url_3', 'image_upload_3', 'clear_upload_3')
        _page['image_url'] = data.get('image_url')
        _page['image_url_2'] = data.get('image_url_2')
        _page['image_url_3'] = data.get('image_url_3')

        if 'type' in _page and _page['type'] == 'data':
            _page['map'] = []
            _page['map_main_property'] = []

            for k, v in sorted(data.items()):
                if k.startswith('map_main_property'):
                    _page['map_main_property'].append(v)
                elif k.startswith('map_') and not k.startswith('map_enabled'):
                    _page['map'].append(v)

            _page['map'] = ';'.join(_page['map'])
            _page['map_main_property'] = ';'.join(_page['map_main_property'])

            topics = []

            for k, v in data.items():
                item = {}

                if k.startswith('topic_title'):
                    id = k[-1]
                    item['title'] = data['topic_title_{}'.format(id)]
                    item['enabled'] = data['topic_enabled_{}'.format(id)]
                    item['subdashboard'] = data['topic_subdashboard_{}'.format(id)]
                    item['order'] = data['topic_order_{}'.format(id)]

                    image_url = data['topic_image_url_{}'.format(id)]

                    # Upload images for topics
                    if h.uploads_enabled():
                        topic_image_url = 'topic_image_upload_{}'.format(id)
                        _upload_image_for_portal(
                            data,
                            topic_image_url,
                            'topic_image_upload_{}'.format(id),
                            'topic_clear_upload_{}'.format(id)
                        )
                        image_url = data.get(topic_image_url)

                    item['image_url'] = image_url

                    topics.append(item)

            _page['topics'] = json.dumps(topics)

        _page.update(data)
        _page['org_name'] = org_name
        _page['id'] = org_name
        _page['page_name'] = page

        try:
            junk = p.toolkit.get_action('orgportals_pages_update')(
                {'user': p.toolkit.c.user or p.toolkit.c.author},
                data_dict=_page
            )
        except p.toolkit.ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return orgportals_pages_edit(org_name,'/' + page, data,
                                   errors, error_summary)

        if ckan_29_or_higher:
            route = 'orgportals_blueprint.pages_index'
        else:
            route = 'orgportals_pages_index'
        redirect_url = p.toolkit.url_for(route, org_name=org_name)
        return p.toolkit.redirect_to(redirect_url)

    try:
        p.toolkit.check_access('orgportals_pages_update', {'user': p.toolkit.c.user or p.toolkit.c.author}, {'id': org_name})
    except p.toolkit.NotAuthorized:
        p.toolkit.abort(401, _('Unauthorized to create or edit a page'))

    if not data:
        data = _page

    errors = errors or {}
    error_summary = error_summary or {}

    if data.get('topics') and len(data.get('topics')) > 0:
        data['topics'] = json.loads(data['topics'])
        data['topics'].sort(key=itemgetter('order'))

    # if _page:
    #     data_dict = {'org_name': org_name}
    #     subdashboards = p.toolkit.get_action('orgportals_subdashboards_list')({}, data_dict)
    #     subdashboards = [{'value': subdashboard['name'], 'text': subdashboard['name']} for subdashboard in subdashboards]
    #     subdashboards.insert(0, {'value': '$none$', 'text':'None'})
    #     data['subdashboards'] = subdashboards

    group_dict = _get_group_dict(org_name)
    c.group_dict = group_dict

    vars = {'data': data, 'errors': errors,
            'error_summary': error_summary,
            'group_dict': group_dict, 'group_type': 'organization',
            'page': _page}

    return p.toolkit.render('organization/pages_edit.html', extra_vars=vars)


def orgportals_pages_delete(org_name, page):
    data_dict = {
        'org_name': org_name,
        'page_name': page
    }

    try:
        if p.toolkit.request.method == 'POST':
            p.toolkit.get_action('orgportals_pages_delete')({}, data_dict)
            if ckan_29_or_higher:
                route = 'orgportals_blueprint.pages_index'
            else:
                route = 'orgportals_pages_index'
            redirect_url = p.toolkit.url_for(route, org_name=org_name)
            return tk.redirect_to(redirect_url)
        else:
            p.toolkit.abort(404, _('Page Not Found'))
    except p.toolkit.NotAuthorized:
        p.toolkit.abort(401, _('Unauthorized to delete page'))
    except p.toolkit.ObjectNotFound:
        p.toolkit.abort(404, _('Group not found'))
    return p.toolkit.render('organization/confirm_delete.html', {'page': page})


def orgportals_nav_bar(org_name):
    data_dict = {'org_name': org_name}
    pages = get_action('orgportals_pages_list')({}, data_dict)
    menu = []

    for page in pages:
        data = {
            'page_title': page['page_title'],
            'order': page['order'],
            'name': page['name']
        }
        menu.append(data)

    group_dict = _get_group_dict(org_name)
    c.group_dict = group_dict

    extra_vars = {
        'menu': menu,
        'group_dict': group_dict,
        'group_type': 'organization'
    }

    if p.toolkit.request.method == 'POST':
        data = _get_form_data(tk.request)

        for k, v in data.items():
            if k.startswith('menu_item_name'):
                page_name = k.split('_')[-1]

                data_dict = {
                    'org_name': org_name,
                    'page_name': page_name
                }

                page = get_action('orgportals_pages_show')({}, data_dict)

                page['order'] = int(v)
                page['org_name'] = org_name
                page['id'] = org_name
                page['page_name'] = page_name

                p.toolkit.get_action('orgportals_pages_update')({}, data_dict=page)

        if ckan_29_or_higher:
            route = 'orgportals_blueprint.pages_index'
        else:
            route = 'orgportals_pages_index'
        redirect_url = p.toolkit.url_for(route, org_name=org_name)
        return tk.redirect_to(redirect_url)

    return p.toolkit.render('organization/nav_bar.html', extra_vars=extra_vars)


def view_portal(org_name, source):
    if not _is_portal_active(org_name):
        extra_vars = {'type': 'portal'}

        return p.toolkit.render('portals/snippets/not_active.html', extra_vars=extra_vars)

    data_dict = {
        'org_name': org_name,
        'page_name': 'home'
    }
    page = p.toolkit.get_action('orgportals_pages_show')({}, data_dict)

    is_upload = page['image_url'] and not page['image_url'].startswith('http')

    if is_upload:
        page['image_url'] = '/uploads/portal/{}'.format(page['image_url'])
    
    image_field_list = ['image_url_2','image_url_3']
    for image_field in image_field_list:
        is_upload = page[image_field] and not page[image_field].startswith('http')
        if is_upload:
            page[image_field] = '/uploads/portal/{}'.format(page[image_field])

    extra_vars = {
        'org_name': org_name,
        'page': page,
        'page_name': 'home'
    }
    c.org_name = org_name
    c.page_name = 'home'
    c.source = source

    org = logic.get_action('organization_show')(None, {'id': org_name})
    if 'orgportals_gtm' in org:
        extra_vars['ga_code'] = org['orgportals_gtm']

    return p.toolkit.render('portals/pages/home.html', extra_vars=extra_vars)


def datapage_show(org_name, source):
    data_dict = {'id': org_name, 'include_extras': True}
    org = get_action('organization_show')({}, data_dict)

    if not _is_portal_active(org_name):
        extra_vars = {'type': 'portal'}

        return p.toolkit.render('portals/snippets/not_active.html', extra_vars=extra_vars)

    package_type = 'dataset'

    c.page_name = 'data'
    c.org_name = org_name
    c.source = source

    try:
        context = {
            'model': model,
            'user': c.user or c.author,
            'auth_user_obj': c.userobj
        }

        check_access('site_read', context)
    except p.toolkit.NotAuthorized:
        p.toolkit.abort(401, _('Not authorized to see this page'))

    # unicode format (decoded from utf8)
    q = c.q = request.params.get('q', u'')
    c.query_error = False
    page = h.get_page_number(request.params)

    limit = int(tk.config.get('ckan.datasets_per_page', 20))

    # most search operations should reset the page counter:
    params_nopage = [(k, v) for k, v in request.params.items()
                     if k != 'page']

    def drill_down_url(alternative_url=None, **by):
        return h.add_url_param(alternative_url=alternative_url,
                               controller='package', action='search',
                               new_params=by)

    c.drill_down_url = drill_down_url

    def remove_field(key, value=None, replace=None):
        return h.remove_url_param(key, value=value, replace=replace,
                                  controller='package', action='search')

    c.remove_field = remove_field

    sort_by = request.params.get('sort', None)
    params_nosort = [(k, v) for k, v in params_nopage if k != 'sort']

    def _sort_by(fields):
        """
        Sort by the given list of fields.

        Each entry in the list is a 2-tuple: (fieldname, sort_order)

        eg - [('metadata_modified', 'desc'), ('name', 'asc')]

        If fields is empty, then the default ordering is used.
        """
        params = params_nosort[:]

        if fields:
            sort_string = ', '.join('%s %s' % f for f in fields)
            params.append(('sort', sort_string))
        return search_url(params, package_type)

    c.sort_by = _sort_by

    if not sort_by:
        c.sort_by_fields = []
    else:
        c.sort_by_fields = [field.split()[0]
                            for field in sort_by.split(',')]

    def pager_url(q=None, page=None):
        params = list(params_nopage)
        params.append(('page', page))
        return search_url(params, package_type)

    c.search_url_params = urlencode(_encode_params(params_nopage))

    try:
        c.fields = []
        # c.fields_grouped will contain a dict of params containing
        # a list of values eg {'tags':['tag1', 'tag2']}
        c.fields_grouped = {}
        search_extras = {}
        fq = ''
        for (param, value) in request.params.items():
            if param not in ['q', 'page', 'sort'] \
                    and len(value) and not param.startswith('_'):
                if not param.startswith('ext_'):
                    c.fields.append((param, value))
                    fq += ' %s:"%s"' % (param, value)
                    if param not in c.fields_grouped:
                        c.fields_grouped[param] = [value]
                    else:
                        c.fields_grouped[param].append(value)
                else:
                    search_extras[param] = value

        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'for_view': True,
                   'auth_user_obj': c.userobj}

        if package_type and package_type != 'dataset':
            # Only show datasets of this particular type
            fq += ' +dataset_type:{type}'.format(type=package_type)
        else:
            # Unless changed via config options, don't show non standard
            # dataset types on the default search page
            if not tk.asbool(
                    tk.config.get('ckan.search.show_all_types', 'False')):
                fq += ' +dataset_type:dataset'

        facets = OrderedDict()

        default_facet_titles = {
            'organization': _('Organizations'),
            'groups': _('Groups'),
            'tags': _('Tags'),
            'res_format': _('Formats'),
            'license_id': _('Licenses'),
        }

        for facet in h.facets():
            if facet in default_facet_titles:
                facets[facet] = default_facet_titles[facet]
            else:
                facets[facet] = facet

        # Facet titles
        for plugin in p.PluginImplementations(p.IFacets):
            facets = plugin.dataset_facets(facets, package_type)

        c.facet_titles = facets

        fq += ' +organization:"{}"'.format(org_name)

        data_dict = {
            'q': q,
            'fq': fq.strip(),
            'facet.field': list(facets.keys()),
            'rows': limit,
            'start': (page - 1) * limit,
            'sort': sort_by,
            'extras': search_extras
        }

        query = get_action('package_search')(context, data_dict)
        c.sort_by_selected = query['sort']

        c.page = h.Page(
            collection=query['results'],
            page=page,
            url=pager_url,
            item_count=query['count'],
            items_per_page=limit
        )
        c.facets = query['facets']
        c.search_facets = query['search_facets']
        c.page.items = query['results']
    except SearchError as se:
        log.error('Dataset search error: %r', se.args)
        c.query_error = True
        c.facets = {}
        c.search_facets = {}
        c.page = h.Page(collection=[])

    c.search_facets_limits = {}
    for facet in c.search_facets.keys():
        try:
            limit = int(request.params.get('_%s_limit' % facet,
                        int(tk.config.get('search.facets.default', 10))))
        except ValueError:
            p.toolkit.abort(400, _('Parameter "{parameter_name}" is not '
                                   'an integer').format(
                            parameter_name='_%s_limit' % facet))
        c.search_facets_limits[facet] = limit

    _setup_template_variables(context, {},
                              package_type=package_type)

    data_dict = {
        'org_name': org['name'],
        'page_name': 'data'
    }
    data_page = p.toolkit.get_action('orgportals_pages_show')({}, data_dict)

    if len(data_page['topics']) > 0:
        data_page['topics'] = json.loads(data_page['topics'])
        data_page['topics'].sort(key=itemgetter('order'))
    else:
        data_page['topics'] = []

    # subdashboards_list = p.toolkit.get_action('orgportals_subdashboards_list')(context, {'org_name': org['name']})
    # subdashboards_dict = {x['name']: x for x in subdashboards_list}
    for topic in data_page['topics']:
        is_upload = topic['image_url'] and not topic['image_url'].startswith('http')

        if is_upload:
            topic['image_url'] = '/uploads/portal/{}'.format(topic['image_url'])

        # if topic['subdashboard'] in subdashboards_dict:
        #     topic['full_attributes'] = subdashboards_dict[topic['subdashboard']]

    extra_vars = {
        'organization': org,
        'org_name': org_name,
        'data_page': data_page,
        'page_name': 'data'
    }

    return p.toolkit.render('portals/pages/data.html',
                            extra_vars=extra_vars)


def library_show(org_name, source):
    data_dict = {'id': org_name, 'include_extras': True}
    org = get_action('organization_show')({}, data_dict)

    if not _is_portal_active(org_name):
        extra_vars = {'type': 'portal'}

        return p.toolkit.render('portals/snippets/not_active.html', extra_vars=extra_vars)

    package_type = 'dataset'

    c.page_name = 'library'
    c.org_name = org_name
    c.source = source

    try:
        context = {
            'model': model,
            'user': c.user or c.author,
            'auth_user_obj': c.userobj
        }

        check_access('site_read', context)
    except p.toolkit.NotAuthorized:
        p.toolkit.abort(401, _('Not authorized to see this page'))

    # unicode format (decoded from utf8)
    q = c.q = request.params.get('q', u'')
    c.query_error = False
    page = h.get_page_number(request.params)

    limit = int(tk.config.get('ckan.datasets_per_page', 20))

    # most search operations should reset the page counter:
    params_nopage = [(k, v) for k, v in request.params.items()
                     if k != 'page']

    def drill_down_url(alternative_url=None, **by):
        return h.add_url_param(alternative_url=alternative_url,
                               controller='package', action='search',
                               new_params=by)

    c.drill_down_url = drill_down_url

    def remove_field(key, value=None, replace=None):
        return h.remove_url_param(key, value=value, replace=replace,
                                  controller='package', action='search')

    c.remove_field = remove_field

    sort_by = request.params.get('sort', None)
    params_nosort = [(k, v) for k, v in params_nopage if k != 'sort']

    def _sort_by(fields):
        """
        Sort by the given list of fields.
        Each entry in the list is a 2-tuple: (fieldname, sort_order)
        eg - [('metadata_modified', 'desc'), ('name', 'asc')]
        If fields is empty, then the default ordering is used.
        """
        params = params_nosort[:]

        if fields:
            sort_string = ', '.join('%s %s' % f for f in fields)
            params.append(('sort', sort_string))
        return search_url(params, package_type)

    c.sort_by = _sort_by

    if not sort_by:
        c.sort_by_fields = []
    else:
        c.sort_by_fields = [field.split()[0]
                            for field in sort_by.split(',')]

    def pager_url(q=None, page=None):
        params = list(params_nopage)
        params.append(('page', page))
        return search_url(params, package_type)

    c.search_url_params = urlencode(_encode_params(params_nopage))

    try:
        c.fields = []
        # c.fields_grouped will contain a dict of params containing
        # a list of values eg {'tags':['tag1', 'tag2']}
        c.fields_grouped = {}
        search_extras = {}
        fq = ''
        for (param, value) in request.params.items():
            if param not in ['q', 'page', 'sort'] \
                    and len(value) and not param.startswith('_'):
                if not param.startswith('ext_'):
                    c.fields.append((param, value))
                    fq += ' %s:"%s"' % (param, value)
                    if param not in c.fields_grouped:
                        c.fields_grouped[param] = [value]
                    else:
                        c.fields_grouped[param].append(value)
                else:
                    search_extras[param] = value

        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'for_view': True,
                   'auth_user_obj': c.userobj}

        if package_type and package_type != 'dataset':
            # Only show datasets of this particular type
            fq += ' +dataset_type:{type}'.format(type=package_type)
        else:
            # Unless changed via config options, don't show non standard
            # dataset types on the default search page
            if not tk.asbool(
                    tk.config.get('ckan.search.show_all_types', 'False')):
                fq += ' +dataset_type:dataset'

        facets = OrderedDict()

        default_facet_titles = {
            'groups': _('Groups'),
            'tags': _('Tags'),
            'license_id': _('Licenses'),
        }

        for facet in h.facets():
            if facet in default_facet_titles:
                facets[facet] = default_facet_titles[facet]
            else:
                facets[facet] = facet

        # Remove res_format facet
        facets.pop('res_format', None)

        # Facet titles
        for plugin in p.PluginImplementations(p.IFacets):
            facets = plugin.dataset_facets(facets, package_type)

        c.facet_titles = facets

        fq += ' +organization:"{}"'.format(org_name)
        fq += ' +res_format:"{}"'.format('PDF')

        data_dict = {
            'q': q,
            'fq': fq.strip(),
            'facet.field': list(facets.keys()),
            'rows': limit,
            'start': (page - 1) * limit,
            'sort': sort_by,
            'extras': search_extras
        }

        query = get_action('package_search')(context, data_dict)

        c.sort_by_selected = query['sort']

        c.page = h.Page(
            collection=query['results'],
            page=page,
            url=pager_url,
            item_count=query['count'],
            items_per_page=limit
        )
        c.facets = query['facets']
        c.search_facets = query['search_facets']
        c.page.items = query['results']
    except SearchError as se:
        log.error('Dataset search error: %r', se.args)
        c.query_error = True
        c.facets = {}
        c.search_facets = {}
        c.page = h.Page(collection=[])
    c.search_facets_limits = {}
    for facet in c.search_facets.keys():
        try:
            limit = int(request.params.get('_%s_limit' % facet,
                        int(tk.config.get('search.facets.default', 10))))
        except ValueError:
            p.toolkit.abort(400, _('Parameter "{parameter_name}" is not '
                                   'an integer').format(
                            parameter_name='_%s_limit' % facet))
        c.search_facets_limits[facet] = limit

    _setup_template_variables(context, {},
                                   package_type=package_type)

    data_dict = {
        'org_name': org['name'],
        'page_name': 'data'
    }
    data_page = p.toolkit.get_action('orgportals_pages_show')({}, data_dict)

    if len(data_page['topics']) > 0:
        data_page['topics'] = json.loads(data_page['topics'])
        data_page['topics'].sort(key=itemgetter('order'))
    else:
        data_page['topics'] = []

    # subdashboards_list = p.toolkit.get_action('orgportals_subdashboards_list')(context, {'org_name': org['name']})
    # subdashboards_dict = {x['name']: x for x in subdashboards_list}
    for topic in data_page['topics']:
        is_upload = topic['image_url'] and not topic['image_url'].startswith('http')

        if is_upload:
            topic['image_url'] = '/uploads/portal/{}'.format(topic['image_url'])

        # if topic['subdashboard'] in subdashboards_dict:
        #     topic['full_attributes'] = subdashboards_dict[topic['subdashboard']]

    data_page['page_title'] = 'Library'
    data_page['name'] = 'library'

    extra_vars = {
        'organization': org,
        'org_name': org_name,
        'data_page': data_page,
        'page_name': 'library'
    }

    return p.toolkit.render('portals/pages/library.html',
                            extra_vars=extra_vars)


def contentpage_show(org_name, page_name, source):
    if not _is_portal_active(org_name):
        extra_vars = {'type': 'portal'}

        return p.toolkit.render('portals/snippets/not_active.html', extra_vars=extra_vars)

    data_dict = {
        'org_name': org_name,
        'page_name': page_name
    }

    page = p.toolkit.get_action('orgportals_pages_show')({}, data_dict)

    is_upload = page['image_url'] and not page['image_url'].startswith('http')

    if is_upload:
        page['image_url'] = '/uploads/portal/{}'.format(page['image_url'])

    if page_name == 'contact' and p.toolkit.request.method == 'POST':
        data = _get_form_data(tk.request)
        content = data['contact_message']
        subject = data['contact_message'][:10] + '...'
        to = data['contact_email']

        response_message = emailer.send_email(content, subject, to)
        page['contact_response_message'] = response_message

    extra_vars = {
        'page': page
    }
    c.org_name = org_name
    c.source = source

    return p.toolkit.render('portals/pages/{0}.html'.format(page_name), extra_vars=extra_vars)


def custompage_show(org_name, page_name, source):
    if not _is_portal_active(org_name):
        extra_vars = {'type': 'portal'}

        return p.toolkit.render('portals/snippets/not_active.html', extra_vars=extra_vars)

    data_dict = {
        'org_name': org_name,
        'page_name': page_name
    }
    data = p.toolkit.get_action('orgportals_pages_show')({}, data_dict)

    is_upload = data['image_url'] and not data['image_url'].startswith('http')

    if is_upload:
        data['image_url'] = '/uploads/portal/{}'.format(data['image_url'])

    extra_vars = {
        'data': data
    }
    c.org_name = org_name
    c.source = source

    return p.toolkit.render('portals/pages/custom.html', extra_vars=extra_vars)


def _get_full_name_authors(context, org_name, group):
    # "rows" is set to a big number because by default Solr will
    # return only 10 rows, and we need all datasets
    all_packages_dict = {
        'fq': '+dataset_type:dataset +organization:' + org_name,
        'rows': 10000000
    }

    if group:
        all_packages_dict.update({'fq': all_packages_dict['fq'] + ' +groups:' + group})

    # Find all datasets for the current organization
    datasets_query = get_action('package_search')(context,
                                                  all_packages_dict)

    full_name_authors = set()
    authors_list = []

    for dataset in datasets_query['results']:
        if dataset.get('author'):
            full_name_authors.add(dataset['author'])

    for author in full_name_authors:
        authors_list.append({
            'name': author,
            'display_name': author,
            'count': 1
        })

    return authors_list


def orgportals_subdashboards_index(org_name):
    data_dict = {'org_name': org_name}
    subdashboards = get_action('orgportals_subdashboards_list')({}, data_dict)
    c.subdashboards = subdashboards

    group_dict = _get_group_dict(org_name)
    c.group_dict = group_dict

    extra_vars = {
        'subdashboards': subdashboards,
        'group_dict': group_dict,
        'group_type': 'organization'
    }

    return p.toolkit.render('organization/subdashboards_list.html', extra_vars=extra_vars)


def orgportals_subdashboards_edit(org_name, subdashboard=None, data=None, errors=None, error_summary=None):
    data_dict = {
        'org_name': org_name,
        'subdashboard_name': subdashboard
    }
    _subdashboard = get_action('orgportals_subdashboards_show')({}, data_dict)

    if _subdashboard is None and len(subdashboard) > 0:
        p.toolkit.abort(404, _('Subdashboard not found.'))

    if _subdashboard is None:
        _subdashboard = {}

    if p.toolkit.request.method == 'POST' and not data:
        data = _get_form_data(tk.request)

        media_items = []
        for k, v in data.items():
            item = {}

            if k.startswith('media_type'):
                id = k.split('_')[-1]
                if data['media_type_{}'.format(id)] == 'chart':

                    item['order'] = int(id)
                    item['media_type'] = data['media_type_{}'.format(id)]
                    item['media_size'] = data['media_size_{}'.format(id)]
                    item['chart_resourceview'] = data['chart_resourceview_{}'.format(id)]
                    item['chart_subheader'] = data['chart_subheader_{}'.format(id)]

                    media_items.append(item)
                elif data['media_type_{}'.format(id)] == 'youtube_video':
                    item['order'] = int(id)
                    item['media_type'] = data['media_type_{}'.format(id)]
                    item['video_source'] = data['video_source_{}'.format(id)]
                    item['video_title'] = data['video_title_{}'.format(id)]
                    item['video_size'] = data['video_size_{}'.format(id)]
                    item['video_title_url'] = data.get('video_title_url_{}'.format(id), item['video_source'])

                    media_items.append(item)
                elif data['media_type_{}'.format(id)] == 'image':

                    item['order'] = int(id)
                    item['media_type'] = data['media_type_{}'.format(id)]
                    item['image_title'] = data['media_image_title_{}'.format(id)]
                    item['image_size'] = data.get('media_image_size_{}'.format(id), 'single')
                    item['image_title_url'] = data.get('media_image_title_url_{}'.format(id), '')

                    image_url = data['media_image_url_{}'.format(id)]

                    # Upload images for topics
                    if h.uploads_enabled():
                        media_image_url = 'media_image_url_{}'.format(id)
                        _upload_image_for_portal(
                            data,
                            media_image_url,
                            'media_image_upload_{}'.format(id),
                            'media_clear_upload_{}'.format(id)
                        )
                        image_url = data.get(media_image_url)

                    item['image_url'] = image_url
                    media_items.append(item)

        _subdashboard['media'] = json.dumps(media_items)
        _subdashboard['map'] = []
        _subdashboard['map_main_property'] = []

        for k, v in sorted(data.items()):
            if k.startswith('map_main_property'):
                _subdashboard['map_main_property'].append(v)
            elif k.startswith('map_') and not k.startswith('map_enabled'):
                _subdashboard['map'].append(v)

        _subdashboard['map'] = ';'.join(_subdashboard['map'])
        _subdashboard['map_main_property'] = ';'.join(_subdashboard['map_main_property'])

        _subdashboard.update(data)
        _subdashboard['org_name'] = org_name
        _subdashboard['subdashboard_name'] = subdashboard

        try:
            junk = p.toolkit.get_action('orgportals_subdashboards_update')(
                data_dict=_subdashboard
            )
        except p.toolkit.ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return orgportals_subdashboards_edit(org_name,'/' + subdashboard, data,
                                   errors, error_summary)

        if ckan_29_or_higher:
            route = 'orgportals_blueprint.subdashboards_index'
        else:
            route = 'orgportals_subdashboards_index'
        redirect_url = p.toolkit.url_for(route, org_name=org_name)
        return tk.redirect_to(redirect_url)

    try:
        p.toolkit.check_access('orgportals_subdashboards_update', {'user': p.toolkit.c.user or p.toolkit.c.author}, {'id': org_name})
    except p.toolkit.NotAuthorized:
        p.toolkit.abort(401, _('Unauthorized to create or edit a subdashboard'))

    if not data:
        data = _subdashboard

    errors = errors or {}
    error_summary = error_summary or {}

    if 'media' in data and len(data['media']) > 0:
        data['media'] = json.loads(data['media'])
        data['media'].sort(key=itemgetter('order'))

    groups = p.toolkit.get_action('group_list')({}, {})
    groups = [{'value': group, 'text': group} for group in groups]
    groups.insert(0, {'value': '$none$', 'text':'None'})
    data['groups'] = groups

    group_dict = _get_group_dict(org_name)
    c.group_dict = group_dict

    vars = {'data': data, 'errors': errors,
            'error_summary': error_summary,
            'group_dict': group_dict, 'group_type': 'organization',
            'subdashboard': _subdashboard}

    return p.toolkit.render('organization/subdashboards_edit.html', extra_vars=vars)


def orgportals_subdashboards_delete(org_name, subdashboard):
    data_dict = {
        'org_name': org_name,
        'subdashboard_name': subdashboard
    }

    try:
        if p.toolkit.request.method == 'POST':
            p.toolkit.get_action('orgportals_subdashboards_delete')({}, data_dict)

            data_dict = {
                'org_name': org_name,
                'page_name': 'data'
            }

            page = get_action('orgportals_pages_show')({}, data_dict)

            topics = page['topics']

            if len(topics) > 0:
                topics = json.loads(topics)
                topics = [item for item in topics if item['subdashboard'] != subdashboard]

                page['topics'] = json.dumps(topics)
                page['page_name'] = 'data'

                p.toolkit.get_action('orgportals_pages_update')({}, page)

            if ckan_29_or_higher:
                route = 'orgportals_blueprint.subdashboards_index'
            else:
                route = 'orgportals_subdashboards_index'
            redirect_url = p.toolkit.url_for(route, org_name=org_name)
            return tk.redirect_to(redirect_url)
        else:
            p.toolkit.abort(404, _('Subdashboard Not Found'))
    except p.toolkit.NotAuthorized:
        p.toolkit.abort(401, _('Unauthorized to delete subdashboard'))
    except p.toolkit.ObjectNotFound:
        p.toolkit.abort(404, _('Group not found'))
    return p.toolkit.render('organization/confirm_delete.html', {'subdashboard': subdashboard})


def subdashboardpage_show(org_name, subdashboard_name, source):
    data_dict = {'id': org_name, 'include_extras': True}
    org = get_action('organization_show')({}, data_dict)

    subdashboards_list = get_action('orgportals_pages_show')({}, {'org_name': org_name, 'page_name': 'data'})
    subdashboards_topics = json.loads(subdashboards_list['topics'])
    subdashboards_dict = {x['subdashboard']: x for x in subdashboards_topics}

    data_dict = {'org_name': org_name, 'subdashboard_name': subdashboard_name}
    subdashboard = get_action('orgportals_subdashboards_show')({}, data_dict)
    subdashboard['subdashboard_title'] = subdashboards_dict[subdashboard['name']]['title']
    org['subdashboards'] = subdashboards_topics

    if not _is_portal_active(org_name):
        extra_vars = {'type': 'portal'}

        return p.toolkit.render('portals/snippets/not_active.html', extra_vars=extra_vars)

    if 'is_active' in subdashboard and subdashboard['is_active'] == False:
        extra_vars = {'type': 'subdashboard'}

        return p.toolkit.render('portals/snippets/not_active.html', extra_vars=extra_vars)

    package_type = 'dataset'

    try:
        context = {
            'model': model,
            'user': c.user or c.author,
            'auth_user_obj': c.userobj
        }

        check_access('site_read', context)
    except p.toolkit.NotAuthorized:
        p.toolkit.abort(401, _('Not authorized to see this page'))

    # unicode format (decoded from utf8)
    q = c.q = request.params.get('q', u'')
    c.query_error = False
    page = h.get_page_number(request.params)

    limit = int(tk.config.get('ckan.datasets_per_page', 20))

    # most search operations should reset the page counter:
    params_nopage = [(k, v) for k, v in request.params.items()
                     if k != 'page']

    def drill_down_url(alternative_url=None, **by):
        return h.add_url_param(alternative_url=alternative_url,
                               controller='package', action='search',
                               new_params=by)

    c.drill_down_url = drill_down_url

    def remove_field(key, value=None, replace=None):
        return h.remove_url_param(key, value=value, replace=replace,
                                  controller='package', action='search')

    c.remove_field = remove_field

    sort_by = request.params.get('sort', None)
    params_nosort = [(k, v) for k, v in params_nopage if k != 'sort']

    def _sort_by(fields):
        """
        Sort by the given list of fields.

        Each entry in the list is a 2-tuple: (fieldname, sort_order)

        eg - [('metadata_modified', 'desc'), ('name', 'asc')]

        If fields is empty, then the default ordering is used.
        """
        params = params_nosort[:]

        if fields:
            sort_string = ', '.join('%s %s' % f for f in fields)
            params.append(('sort', sort_string))
        return search_url(params, package_type)

    c.sort_by = _sort_by

    if not sort_by:
        c.sort_by_fields = []
    else:
        c.sort_by_fields = [field.split()[0]
                            for field in sort_by.split(',')]

    def pager_url(q=None, page=None):
        params = list(params_nopage)
        params.append(('page', page))
        return search_url(params, package_type)

    c.search_url_params = urlencode(_encode_params(params_nopage))

    try:
        c.fields = []
        # c.fields_grouped will contain a dict of params containing
        # a list of values eg {'tags':['tag1', 'tag2']}
        c.fields_grouped = {}
        search_extras = {}
        fq = ''
        for (param, value) in request.params.items():
            if param not in ['q', 'page', 'sort'] \
                    and len(value) and not param.startswith('_'):
                if not param.startswith('ext_'):
                    c.fields.append((param, value))
                    fq += ' %s:"%s"' % (param, value)
                    if param not in c.fields_grouped:
                        c.fields_grouped[param] = [value]
                    else:
                        c.fields_grouped[param].append(value)
                else:
                    search_extras[param] = value

        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'for_view': True,
                   'auth_user_obj': c.userobj}

        if package_type and package_type != 'dataset':
            # Only show datasets of this particular type
            fq += ' +dataset_type:{type}'.format(type=package_type)
        else:
            # Unless changed via config options, don't show non standard
            # dataset types on the default search page
            if not tk.asbool(
                    tk.config.get('ckan.search.show_all_types', 'False')):
                fq += ' +dataset_type:dataset'

        facets = OrderedDict()

        default_facet_titles = {
            'organization': _('Organizations'),
            'groups': _('Groups'),
            'tags': _('Tags'),
            'res_format': _('Formats'),
            'license_id': _('Licenses'),
        }

        for facet in h.facets():
            if facet in default_facet_titles:
                facets[facet] = default_facet_titles[facet]
            else:
                facets[facet] = facet

        # Add 'author' facet
        facets['author'] = _('Authors')

        # Facet titles
        for plugin in p.PluginImplementations(p.IFacets):
            facets = plugin.dataset_facets(facets, package_type)

        c.facet_titles = facets

        fq += ' +organization:"{0}"+groups:{1}'.format(org_name, subdashboard['group'])

        data_dict = {
            'q': q,
            'fq': fq.strip(),
            'facet.field': list(facets.keys()),
            'rows': limit,
            'start': (page - 1) * limit,
            'sort': sort_by,
            'extras': search_extras
        }

        query = get_action('package_search')(context, data_dict)

        # Override the "author" list, to include full name authors
        query['search_facets']['author']['items'] =\
            _get_full_name_authors(context, org_name, subdashboard['group'])

        print('authors', _get_full_name_authors(context, org_name, subdashboard['group']))

        c.sort_by_selected = query['sort']

        c.page = h.Page(
            collection=query['results'],
            page=page,
            url=pager_url,
            item_count=query['count'],
            items_per_page=limit
        )
        c.facets = query['facets']
        c.search_facets = query['search_facets']
        c.page.items = query['results']
    except SearchError as se:
        log.error('Dataset search error: %r', se.args)
        c.query_error = True
        c.facets = {}
        c.search_facets = {}
        c.page = h.Page(collection=[])
    c.search_facets_limits = {}
    for facet in c.search_facets.keys():
        try:
            limit = int(request.params.get('_%s_limit' % facet,
                                           g.facets_default_number or 10))
        except ValueError:
            p.toolkit.abort(400, _('Parameter "{parameter_name}" is not '
                         'an integer').format(
                parameter_name='_%s_limit' % facet))
        c.search_facets_limits[facet] = limit

    _setup_template_variables(context, {},
                                   package_type=package_type)

    if 'media' in subdashboard and len(subdashboard['media']) > 0:
        subdashboard['media'] = json.loads(subdashboard['media'])
        subdashboard['media'].sort(key=itemgetter('order'))

        for item in subdashboard['media']:
            is_upload = 'image_url' in item and item['image_url'] and not item['image_url'].startswith('http')

            if is_upload:
                item['image_url'] = '/uploads/portal/{}'.format(item['image_url'])

    extra_vars = {
        'organization': org,
        'subdashboard': subdashboard
    }
    c.org_name = org_name

    return p.toolkit.render('portals/pages/subdashboard.html', extra_vars=extra_vars)


def show_portal_homepage():
    return _get_portal_page(view_portal)

def show_portal_datapage():
    return _get_portal_page(datapage_show)

def show_portal_contentpage(page_name):
    return _get_portal_page(contentpage_show, page_name)

def show_portal_custompage(page_name):
    return _get_portal_page(custompage_show, page_name)

def show_portal_subdashboardpage(subdashboard_name):
    return _get_portal_page(subdashboardpage_show, subdashboard_name)


def _get_portal_page(callback, requested_page_name=None):
    name = None
    request_url = urlparse(p.toolkit.request.url)
    ckan_base_url = urlparse(tk.config.get('ckan.site_url'))

    if request_url.netloc != ckan_base_url.netloc:

        org_list = get_action('organization_list')({}, {'all_fields': True, 'include_extras': True})

        for org in org_list:
            if 'orgportals_portal_url' in org:
                org_url = urlparse(org['orgportals_portal_url'])
                if org_url.netloc == request_url.netloc:
                    name = org['name']

        if name is None:
            c.url = p.toolkit.request.url
            return p.toolkit.render('portals/snippets/domain_not_registered.html')
        else:
            if requested_page_name is None:
                return callback(name)
            else:
                return callback(name, requested_page_name)

    else:
        return p.toolkit.render('home/index.html')


def _is_portal_active(orgnization_name):
    data_dict = {'id': orgnization_name, 'include_extras': True}
    org = get_action('organization_show')({}, data_dict)

    if 'orgportals_is_active' in org and org['orgportals_is_active'] == '1':
        return True
    else:
        return False
