This package simplifies the calls to Data Hub's API.

No magic. You need to follow the [Data Hub Swagger Documentation](https://api.opinum.com) for correct formatting of your requests

Be aware that this is a new package, certainly missing a lot of features. Feel free to contribute.

You first need to create an instance of the ApiConnector class with following parameters:

*ATTENTION:* this package can only be used from Data Hub version 7.0 (1 July 2025) onward, as it uses the authentication to the the new technology (Keycloak).
For previous versions, the opinum-api-connector package can be used (https://github.com/opinum/opinum-api-connector) instead.

> _environment_
> > a dictionary of environment variables
> >
> > if `None`, ApiConnector uses your environment variables (_os.environ_)
> >
> > Mandatory environment variables are:
> >
> > * _DATAHUB_USERNAME_: the Datahub user. <br>
> > TAKE CARE: if this user has access to multiple tenants and if you do not specify a tenant id,
> > ApiConnector will use the last tenant used.
> > * _DATAHUB_PASSWORD_: the password for the user
> > * _DATAHUB_CLIENT_ID_: the client id for accessing the API
> > * _DATAHUB_CLIENT_SECRET_ the corresponding secret
> > 
> > Optional environment variables are:
> >
> > * _DATAHUB_API_URL_: another API URL than the Europe SaaS one (https://api.opinum.com)
> > * _DATAHUB_AUTH_URL_: another authentication URL than the Europe SaaS one (https://auth.opinum.com)
> > * _DATAHUB_PUSH_URL_: another push URL than the Europe SaaS one (https://push.opinum.com)
> > * _DATAHUB_SCOPE_: the scope of you session (default: "_datahub-api_")<br>
> > if you want to push data, the scope should be "_datahub-api push-data_"

> _account_id_
> > one of the tenant ids available for the Datahub user (default: `None`)

> _retries_when_connection_failure_
> > number of extra attempts when no 200 or 204 return code (default: 0, maximum: 5)

Once you have your ApiConnector instance, you may use the class methods

* get
* post
* patch
* put
* delete
* send_file_to_storage

All keyword arguments will be converted to path parameters in the API call with one important exception,
the _data_ keyword referring to the body of your call.

There are two other class methods for data pushing because we have another API for this

* push_data
* push_dataframe_data

There is a little bit of magic with the method multi_thread_request_on_path that splits a list of parameters
Allowing to make parallel calls.
