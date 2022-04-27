# encoding: utf-8
import ckan.plugins as plugins
from ckan.plugins import toolkit as tk


class MixinPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IRoutes, inherit=True)

    # IRoutes

    def before_map(self, map):
        ctrl = 'ckanext.orgportals.controllers.portals:OrgportalsController'

        #edit portal admin routes
        map.connect('orgportals_pages_delete', '/organization/edit/{org_name}/pages_delete/{page}',
                    action='orgportals_pages_delete', ckan_icon='delete', controller=ctrl)
        map.connect('orgportals_pages_edit', '/organization/edit/{org_name}/pages_edit',
                    action='orgportals_pages_edit', ckan_icon='edit', controller=ctrl, page='')
        map.connect('orgportals_pages_edit', '/organization/edit/{org_name}/pages_edit/{page}',
                    action='orgportals_pages_edit', ckan_icon='edit', controller=ctrl)
        map.connect('orgportals_pages_index', '/organization/edit/{org_name}/pages',
                    action='orgportals_pages_index', ckan_icon='file', controller=ctrl)
        map.connect('orgportals_nav_bar', '/organization/edit/{org_name}/nav', controller=ctrl,
                    action='orgportals_nav_bar', ckan_icon='list')
        map.connect('orgportals_subdashboards_index', '/organization/edit/{org_name}/subdashboards', controller=ctrl,
                    action='orgportals_subdashboards_index', ckan_icon='file')
        map.connect('orgportals_subdashboards_edit', '/organization/edit/{org_name}/subdashboards_edit',
                    action='orgportals_subdashboards_edit', ckan_icon='edit', controller=ctrl, subdashboard='')
        map.connect('orgportals_subdashboards_edit', '/organization/edit/{org_name}/subdashboards_edit/{subdashboard}',
                    action='orgportals_subdashboards_edit', ckan_icon='edit', controller=ctrl)
        map.connect('orgportals_subdashboards_delete', '/organization/edit/{org_name}/subdashboards_delete/{subdashboard}',
                    action='orgportals_subdashboards_delete', ckan_icon='delete', controller=ctrl)


        #portal routes for custom domain
        if tk.asbool(tk.config.get('ckanext.orgdashboards.custom_dns_active')):
            map.connect('orgportals_show_portal_homepage', '/', controller=ctrl, action='show_portal_homepage')
        map.connect('orgportals_show_portal_datapage', '/data', controller=ctrl, action='show_portal_datapage')
        map.connect('orgportals_show_portal_contentpage', '/aboutportal', controller=ctrl, action='show_portal_contentpage', page_name='about')
        map.connect('orgportals_show_portal_custompage', '/org-pages/{page_name}', controller=ctrl, action='show_portal_custompage')
        map.connect('orgportals_show_portal_subdashboardpage', '/subdashboard/{subdashboard_name}', controller=ctrl, action='show_portal_subdashboardpage')


        #portal routes for admin
        map.connect('orgportals_view_portal', '/organization/{org_name}/portal/home', controller=ctrl,
                    action='view_portal', source='admin')
        map.connect('orgportals_datapage_show', '/organization/{org_name}/portal/data', controller=ctrl,
                    action='datapage_show', source='admin')
        map.connect('orgportals_library_show', '/organization/{org_name}/portal/library', controller=ctrl,
                    action='library_show', source='admin')
        map.connect('orgportals_subdashboardpage_show', '/organization/{org_name}/portal/subdashboard/{subdashboard_name}', controller=ctrl,
                    action='subdashboardpage_show', source='admin')
        map.connect('orgportals_contentpage_show', '/organization/{org_name}/portal/about', controller=ctrl,
                    action='contentpage_show', source='admin', page_name='about')
        map.connect('orgportals_custompage_show', '/organization/{org_name}/portal/{page_name}', controller=ctrl,
                    action='custompage_show', source='admin')

        return map
