import logging
from copy import deepcopy

from datahub_api_connector import ApiConnector

logging.basicConfig(level=logging.INFO)


def default_source_callback(source, target_site):
    return source


def default_get_allowed_sources(site, site_content_duplicator):
    return None


def default_get_excluded_sources(site, site_content_duplicator):
    return None


def default_get_allowed_variables(site, source, site_content_duplicator):
    return None


def default_get_excluded_variables(site, source, site_content_duplicator):
    return None


def do_not_process_source(source_key, allowed_sources, excluded_sources):
    not_allowed = allowed_sources is not None and source_key not in allowed_sources
    excluded = excluded_sources is not None and source_key in excluded_sources
    return not_allowed or excluded


def do_not_process_variable(mapping_config, allowed_variables, excluded_variables):
    not_allowed = allowed_variables is not None and mapping_config not in allowed_variables
    excluded = excluded_variables is not None and mapping_config in excluded_variables
    return not_allowed or excluded


class SiteContentDuplicator:
    """
    SiteContentDuplicator allows make a full copy of a site

    This implies a copy of all sources in the site with their variables (raw and calculated)
    """
    def __init__(self, target_site_ids, template_site_id, source_key_field, account_id=None,
                 source_callback=default_source_callback,
                 get_allowed_sources=default_get_allowed_sources,
                 get_excluded_sources=default_get_excluded_sources,
                 get_allowed_variables=default_get_allowed_variables,
                 get_excluded_variables=default_get_excluded_variables,
                 ignore_missing_calculated_inputs=True,
                 update_sources=False,
                 update_variables=False):
        """

        :param target_site_ids: a list of site ids that will host the new sources
        :param template_site_id: the site id that we copy
        :param source_key_field: allows to identify the sources: 'name', 'serialNumber', 'meternumber' or 'eanNumber'
        :param account_id: the tenant id
        :param source_callback: a method that transforms the source received input. Manipulating the source_key_field is allowed.
        :param get_allowed_sources: a method that returns the list of allowed source (via their key) for a given site. None means all sources are allowed.
        :param get_excluded_sources: a method that returns the list of excluded source (via their key) for a given site. None means no exclusion.
        :param get_allowed_variables: a method that returns the list of allowed variables (via their mapping config) for a given site/source. None means all variables are allowed.
        :param get_excluded_variables: a method that returns the list of allowed variables (via their mapping config) for a given site/source. None means all variables are allowed.
        :param ignore_missing_calculated_inputs: tell what to do with calculated variables inputs without associated source or variable in the target site
        :param update: to force updates
        """
        logging.info('Start Site Duplicator')
        self.target_site_ids = target_site_ids
        self.template_site_id = template_site_id
        self.source_key_field = source_key_field
        self.source_callback = source_callback
        self.get_allowed_sources = get_allowed_sources
        self.get_excluded_sources = get_excluded_sources
        self.get_allowed_variables = get_allowed_variables
        self.get_excluded_variables = get_excluded_variables
        self.ignore_missing_calculated_inputs = ignore_missing_calculated_inputs
        self.update_sources = update_sources
        self.update_variables = update_variables
        self.api_connector = ApiConnector(account_id=account_id)
        self.template_sources = dict()
        self.template_vars = dict()
        self.template_var_id_infos = dict()
        for source in self.api_connector.get('sources',
                                             siteId=self.template_site_id,
                                             displayLevel='Site').json():
            logging.info(f"Getting info for source {source[self.source_key_field]}")
            self.template_sources[source['id']] = source
            self.template_vars[source[self.source_key_field]] = dict()
            for variable in self.api_connector.get('variables',
                                                   sourceId=source['id'],
                                                   displayLevel='Verbose').json():
                if 'mappingConfig' not in variable:
                    logging.warning(f"Variable named {variable['name']} has no mapping config. Ignored")
                    continue
                logging.info(f"\tGetting info for variable {variable['mappingConfig']}")
                self.template_vars[source[self.source_key_field]][variable['mappingConfig']] = variable
                self.template_var_id_infos[variable['id']] = {
                    'source': source,
                    'variable': variable
                }

    def process_site(self, site):
        logging.info(f"Processing site {site['name']}")
        existing_sources = {s[self.source_key_field]: s for s in self.api_connector.get('sources',
                                                                                        siteId=site['id'],
                                                                                        displayLevel='Site').json()}
        source_key_mappings = dict()
        allowed_sources = self.get_allowed_sources(site, self)
        excluded_sources = self.get_excluded_sources(site, self)
        for source in self.template_sources.values():
            # key for new source can be different with template
            new_source = self.source_callback(deepcopy(source), site)
            source_key = new_source[self.source_key_field]
            if do_not_process_source(source_key, allowed_sources, excluded_sources):
                logging.info(f"Source {source_key} is excluded from processing")
                continue
            logging.info(f"Checking source {source_key}")
            new_source.pop('siteName')
            new_source['siteId'] = site['id']
            if source_key not in existing_sources:
                logging.info("\tCreating source")
                new_source.pop('id')
                existing_sources[source_key] = self.api_connector.post('sources', data=new_source).json()
            elif self.update_sources:
                logging.info("\tUpdating source")
                new_source['id'] = existing_sources[source_key]['id']
                self.api_connector.put(f"sources/{new_source['id']}", data=new_source)

            source_key_mappings[source[self.source_key_field]] = source_key

        # Second run now that all sources exist
        calculated_variables_templates = dict()
        existing_variables = dict()
        for source_key, source in existing_sources.items():
            if source[self.source_key_field] not in self.template_vars:
                logging.warning(f"Source {source_key} is not existing in template. No variables to handle")
                continue
            if do_not_process_source(source_key, allowed_sources, excluded_sources):
                logging.info(f"Source {source_key} is excluded from processing. No variables to handle")
                continue
            logging.info(f"Checking variables for source {source_key}")
            allowed_variables = self.get_allowed_variables(site, source, self)
            excluded_variables = self.get_excluded_variables(site, source, self)
            existing_variables[source_key] = {v['mappingConfig']: v for v in self.api_connector.get('variables',
                                                                                                    sourceId=source['id'],
                                                                                                    displayLevel='Verbose').json()}
            for mapping, variable in self.template_vars[source[self.source_key_field]].items():
                if do_not_process_variable(mapping, allowed_variables, excluded_variables):
                    logging.info(f"Variable {mapping} is excluded from processing")
                    continue
                new_var = deepcopy(variable)
                new_var['sourceId'] = source['id']
                if mapping in existing_variables[source_key]:
                    if self.update_variables:
                        new_var_id = existing_variables[source_key][mapping]['id']
                        new_var['id'] = new_var_id
                        if 'calculated' in new_var:
                            calculated_variables_templates.setdefault(source_key, list()).append(variable)
                            new_var['calculated']['calculatedVariableFormulas'] = [{}]
                        logging.info(f"\tUpdating variable {mapping}")
                        self.api_connector.put(f"sources/{source['id']}/variables/{new_var_id}", data=new_var)
                else:
                    if 'calculated' in new_var:
                        # Keep another copy for later
                        calculated_variables_templates.setdefault(source_key, list()).append(variable)
                        new_var['calculated']['calculatedVariableFormulas'] = [{}]
                    new_var.pop('id')
                    logging.info(f"\tCreating variable {mapping}")
                    existing_variables[source_key][mapping] = self.api_connector.post(f"variables/source/{source['id']}",
                                                                                      data=new_var).json()

        # Third run now that all variables exist (without calculations possibly)
        for source_key, variables in calculated_variables_templates.items():
            source = existing_sources[source_key]
            logging.info(f"Finalising calculated variables for source {source_key}")
            for new_var in variables:
                mapping = new_var['mappingConfig']
                logging.info(f"\tUpdating variable {mapping}")
                new_var_id = existing_variables[source_key][mapping]['id']
                new_var['id'] = new_var_id
                new_var['sourceId'] = source['id']
                for formula in new_var['calculated']['calculatedVariableFormulas']:
                    new_variables_list = list()
                    for sub_var in formula['variables']:
                        if sub_var['siteId'] != self.template_site_id:
                            new_variables_list.append(deepcopy(sub_var))
                            continue
                        if sub_var['variableId'] not in self.template_var_id_infos:
                            message = (f"Source {sub_source_info['source'][self.source_key_field]} has an input variable"
                                       f" without mapping config.")
                            if self.ignore_missing_calculated_inputs:
                                logging.info(f"{message} Dropped from the list of input variables")
                            else:
                                logging.info(f"{message} We keep the template variable")
                                new_variables_list.append(deepcopy(sub_var))
                            continue
                        sub_source_info = self.template_var_id_infos[sub_var['variableId']]
                        if sub_source_info['source'][self.source_key_field] not in source_key_mappings:
                            message = (f"Source {sub_source_info['source'][self.source_key_field]} has an input variable"
                                       f" but is not covered by this run.")
                            if self.ignore_missing_calculated_inputs:
                                logging.info(f"{message} Dropped from the list of input variables")
                            else:
                                logging.info(f"{message} We keep the template variable")
                                new_variables_list.append(deepcopy(sub_var))
                            continue
                        sub_source_key = source_key_mappings[sub_source_info['source'][self.source_key_field]]
                        sub_mapping = sub_source_info['variable']['mappingConfig']
                        if sub_mapping not in existing_variables[sub_source_key]:
                            message = (f"Variable {sub_mapping} from source {sub_source_key} is an input variable"
                                       f" but is not covered by this run.")
                            if self.ignore_missing_calculated_inputs:
                                logging.info(f"{message} Dropped from the list of input variables")
                            else:
                                logging.info(f"{message} We keep the template variable")
                                new_variables_list.append(deepcopy(sub_var))
                            continue
                        sub_var['siteId'] = site['id']
                        sub_var['sourceId'] = existing_sources[sub_source_key]['id']
                        sub_var['variableId'] = existing_variables[sub_source_key][sub_mapping]['id']
                        new_variables_list.append(sub_var)
                    formula['variables'] = new_variables_list
                    new_entities_list = list()
                    for form_value in formula['entities']:
                        if form_value['siteId'] != self.template_site_id:
                            new_entities_list.append(deepcopy(form_value))
                            continue
                        new_form_value = deepcopy(form_value)
                        if new_form_value['entityType'] == 1: # Site form
                            new_form_value['siteId'] = site['id']
                            new_form_value['entityId'] = site['id']
                            new_entities_list.append(new_form_value)
                            continue
                        sub_source = self.template_sources[form_value['sourceId']]
                        if sub_source[self.source_key_field] not in source_key_mappings:
                            message = (f"Source {sub_source_info['source'][self.source_key_field]} has an input form field"
                                       f" but is not covered by this run.")
                            if self.ignore_missing_calculated_inputs:
                                logging.info(f"{message} Dropped from the list of input form fields")
                            else:
                                logging.info(f"{message} We keep the template form field")
                                new_entities_list.append(new_form_value)
                            continue
                        sub_source_key = source_key_mappings[sub_source_info['source'][self.source_key_field]]
                        new_form_value['siteId'] = site['id']
                        new_form_value['sourceId'] = existing_sources[sub_source_key]['id']
                        new_form_value['entityId'] = existing_sources[sub_source_key]['id']
                        new_entities_list.append(new_form_value)
                    formula['entities'] = new_entities_list
                self.api_connector.put(f"sources/{source['id']}/variables/{new_var_id}", data=new_var)
                existing_variables[mapping] = new_var

    def run(self):
        for site_id in self.target_site_ids:
            site = self.api_connector.get('sites', siteIds=[site_id], displayLevel='VerboseSite').json()[0]
            self.process_site(site)

