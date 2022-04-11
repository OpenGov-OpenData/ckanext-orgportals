from ckan.controllers.package import PackageController
import ckanext.orgportals.utils as utils


class OrgportalsController(PackageController):
    def orgportals_pages_index(self, org_name):
        return utils.orgportals_pages_index(org_name)

    def orgportals_pages_edit(self, org_name, page):
        return utils.orgportals_pages_edit(org_name, page)

    def orgportals_pages_delete(self, org_name, page):
        return utils.orgportals_pages_delete(org_name, page)

    def orgportals_nav_bar(self, org_name):
        return utils.orgportals_nav_bar(org_name)

    def view_portal(self, org_name, source):
        return utils.view_portal(org_name, source)

    def datapage_show(self, org_name, source):
        return utils.datapage_show(org_name, source)

    def library_show(self, org_name, source):
        return utils.library_show(org_name, source)

    def contentpage_show(self, org_name, source, page_name):
        return utils.contentpage_show(org_name, source, page_name)

    def custompage_show(self, org_name, source, page_name):
        return utils.custompage_show(org_name, source, page_name)

    def orgportals_subdashboards_index(self, org_name):
        return utils.orgportals_subdashboards_index(org_name)

    def orgportals_subdashboards_edit(self, org_name, subdashboard):
        return utils.orgportals_subdashboards_edit(org_name, subdashboard)

    def orgportals_subdashboards_delete(self, org_name, subdashboard):
        return utils.orgportals_subdashboards_delete(org_name, subdashboard)

    def subdashboardpage_show(self, org_name, subdashboard_name, source):
        return utils.subdashboardpage_show(org_name, subdashboard_name, source)

    def show_portal_homepage(self):
        return utils.show_portal_homepage()

    def show_portal_datapage(self):
        return utils.show_portal_datapage()

    def show_portal_contentpage(self):
        return utils.show_portal_contentpage()

    def show_portal_custompage(self, page_name):
        return utils.show_portal_custompage(page_name)

    def show_portal_subdashboardpage(self, subdashboard_name):
        return utils.show_portal_subdashboardpage(subdashboard_name)
