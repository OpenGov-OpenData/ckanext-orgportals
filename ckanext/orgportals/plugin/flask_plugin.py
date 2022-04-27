# encoding: utf-8
import ckan.plugins as plugins
import ckanext.orgportals.views as views


class MixinPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IBlueprint)

    # IBlueprint
    def get_blueprint(self):
        return views.get_blueprints()
