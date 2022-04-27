# encoding: utf-8
from flask import Blueprint
import ckan.plugins.toolkit as tk
import ckanext.orgportals.utils as utils


orgportals = Blueprint(u'orgportals_blueprint', __name__)


def orgportals_pages_index(org_name):
    return utils.orgportals_pages_index(org_name)


def orgportals_pages_edit(org_name, page):
    return utils.orgportals_pages_edit(org_name, page)


def orgportals_pages_delete(org_name, page):
    return utils.orgportals_pages_delete(org_name, page)


def orgportals_nav_bar(org_name):
    return utils.orgportals_nav_bar(org_name)


def view_portal(org_name, source):
    return utils.view_portal(org_name, source)


def datapage_show(org_name, source):
    return utils.datapage_show(org_name, source)


def library_show(org_name, source):
    return utils.library_show(org_name, source)


def contentpage_show(org_name, page_name, source):
    return utils.contentpage_show(org_name, page_name, source)


def custompage_show(org_name, page_name, source):
    return utils.custompage_show(org_name, page_name, source)


def orgportals_subdashboards_index(org_name):
    return utils.orgportals_subdashboards_index(org_name)


def orgportals_subdashboards_edit(org_name, subdashboard):
    return utils.orgportals_subdashboards_edit(org_name, subdashboard)


def orgportals_subdashboards_delete(org_name, subdashboard):
    return utils.orgportals_subdashboards_delete(org_name, subdashboard)


def subdashboardpage_show(org_name, subdashboard_name, source):
    return utils.subdashboardpage_show(org_name, subdashboard_name, source)


def show_portal_homepage(self):
    return utils.show_portal_homepage()

def show_portal_datapage(self):
    return utils.show_portal_datapage()

def show_portal_contentpage(self):
    return utils.show_portal_contentpage()

def show_portal_custompage(page_name):
    return utils.show_portal_custompage(page_name)

def show_portal_subdashboardpage(subdashboard_name):
    return utils.show_portal_subdashboardpage(subdashboard_name)


orgportals.add_url_rule(
    '/organization/edit/<org_name>/pages',
    'pages_index',
    view_func=orgportals_pages_index,
    methods=[u'GET', u'POST']
)

orgportals.add_url_rule(
    '/organization/edit/<org_name>/pages_edit',
    'pages_edit',
    view_func=orgportals_pages_edit,
    defaults={'page': ''},
    methods=[u'GET', u'POST']
)
orgportals.add_url_rule(
    '/organization/edit/<org_name>/pages_edit/<page>',
    'pages_edit',
    view_func=orgportals_pages_edit,
    methods=[u'GET', u'POST']
)

orgportals.add_url_rule(
    '/organization/edit/<org_name>/pages_delete/<page>',
    'pages_delete',
    view_func=orgportals_pages_delete,
    methods=[u'GET', u'POST']
)

orgportals.add_url_rule(
    '/organization/edit/<org_name>/nav',
    'nav_bar',
    view_func=orgportals_nav_bar,
    methods=[u'GET', u'POST']
)

orgportals.add_url_rule(
    '/organization/<org_name>/portal/home',
    'view_portal',
    view_func=view_portal,
    defaults={'source': 'admin'}
)

orgportals.add_url_rule(
    '/organization/<org_name>/portal/data',
    'datapage_show',
    view_func=datapage_show,
    defaults={'source': 'admin'}
)

orgportals.add_url_rule(
    '/organization/<org_name>/portal/library',
    'library_show',
    view_func=library_show,
    defaults={'source': 'admin'}
)

orgportals.add_url_rule(
    '/organization/<org_name>/portal/about',
    'contentpage_show',
    view_func=contentpage_show,
    defaults={'source': 'admin', 'page_name': 'about'}
)

orgportals.add_url_rule(
    '/organization/<org_name>/portal/<page_name>',
    'custompage_show',
    view_func=custompage_show,
    defaults={'source': 'admin'}
)

orgportals.add_url_rule(
    '/organization/edit/<org_name>/subdashboards',
    'subdashboards_index',
    view_func=orgportals_subdashboards_index
)

orgportals.add_url_rule(
    '/organization/edit/<org_name>/subdashboards_edit',
    'subdashboards_edit',
    view_func=orgportals_subdashboards_edit,
    defaults={'subdashboard': ''}
)
orgportals.add_url_rule(
    '/organization/edit/<org_name>/subdashboards_edit/<subdashboard>',
    'subdashboards_edit',
    view_func=orgportals_subdashboards_edit
)

orgportals.add_url_rule(
    '/organization/edit/<org_name>/subdashboards_delete/<subdashboard>',
    'subdashboards_delete',
    view_func=orgportals_subdashboards_delete
)

orgportals.add_url_rule(
    '/organization/<org_name>/portal/subdashboard/<subdashboard_name>',
    'subdashboardpage_show',
    view_func=subdashboardpage_show,
    defaults={'source': 'admin'}
)

if tk.asbool(tk.config.get('ckanext.orgdashboards.custom_dns_active')):
    orgportals.add_url_rule(
        '/',
        'show_portal_homepage',
        view_func=show_portal_homepage
    )

orgportals.add_url_rule(
    '/data',
    'show_portal_datapage',
    view_func=show_portal_datapage
)

orgportals.add_url_rule(
    '/aboutportal',
    'show_portal_contentpage',
    view_func=show_portal_contentpage,
    defaults={'page_name': 'about'}
)

orgportals.add_url_rule(
    '/org-pages/<page_name>',
    'show_portal_custompage',
    view_func=show_portal_custompage
)

orgportals.add_url_rule(
    '/subdashboard/<subdashboard_name>',
    'show_portal_subdashboardpage',
    view_func=show_portal_subdashboardpage
)


def get_blueprints():
    return [orgportals]
