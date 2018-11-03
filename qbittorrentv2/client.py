import requests
import json


class LoginRequired(Exception):
    def __str__(self):
        return 'Please login first.'


class Client(object):
    """class to interact with qBittorrent WEB API"""
    def __init__(self, url):
        if not url.endswith('/api/v2/'):
            url += '/api/v2/'
        self.url = url

        session = requests.Session()
        check_prefs = session.get(url+'app/preferences')

        if check_prefs.status_code == 200:
            self._is_authenticated = True
            self.session = session

        elif check_prefs.status_code == 404:
            self._is_authenticated = False
            raise RuntimeError("""
                This wrapper only supports qBittorrent applications
                 with version higher than 3.1.x.
                 Please use the latest qBittorrent release.
                """)

        else:
            self._is_authenticated = False


    """ 
    Request Methods
    """


    def _get(self, endpoint, **kwargs):
        """
        Method to perform GET request on the API.

        :param endpoint: Endpoint of the API.
        :param kwargs: Other keyword arguments for requests.

        :return: Response of the GET request.
        """
        return self._request(endpoint, 'get', **kwargs)

    def _post(self, endpoint, data, **kwargs):
        """
        Method to perform POST request on the API.

        :param endpoint: Endpoint of the API.
        :param data: POST DATA for the request.
        :param kwargs: Other keyword arguments for requests.

        :return: Response of the POST request.
        """
        return self._request(endpoint, 'post', data, **kwargs)

    def _request(self, endpoint, method, data=None, **kwargs):
        """
        Method to hanle both GET and POST requests.

        :param endpoint: Endpoint of the API.
        :param method: Method of HTTP request.
        :param data: POST DATA for the request.
        :param kwargs: Other keyword arguments.

        :return: Response for the request.
        """
        final_url = self.url + endpoint

        if not self._is_authenticated:
            raise LoginRequired

        rq = self.session
        if method == 'get':
            request = rq.get(final_url, **kwargs)
        else:
            request = rq.post(final_url, data, **kwargs)

        request.raise_for_status()
        request.encoding = 'utf_8'

        if len(request.text) == 0:
            data = json.loads('{}')
        else:
            try:
                data = json.loads(request.text)
            except ValueError:
                data = request.text

        return data


    """
    Authentication methods
    """


    def login(self, username='admin', password='admin'):
        """
        Method to authenticate the qBittorrent Client.

        Declares a class attribute named ``session`` which
        stores the authenticated session if the login is correct.
        Else, shows the login error.

        :param username: Username.
        :param password: Password.

        :return: Response to login request to the API.
        """
        self.session = requests.Session()
        login = self.session.post(self.url+'auth/login',
                                  data={'username': username,
                                        'password': password})
        if login.text == 'Ok.':
            self._is_authenticated = True
        else:
            return login.text

    def logout(self):
        """
        Logout the current session.
        """
        response = self._get('auth/logout')
        self._is_authenticated = False
        return response


    """
    Application methods
    """

    @property
    def qbittorrent_version(self):
        """
        Get qBittorrent version.
        """
        return self._get('app/version')

    @property
    def api_version(self):
        """
        Get WEB API version.
        """
        return self._get('app/webapiVersion')

    def shutdown(self):
        """
        Shutdown qBittorrent.
        """
        return self._get('app/shutdown')

    @property
    def preferences(self):
        """
        Get the current qBittorrent preferences.
        Can also be used to assign individual preferences.
        For setting multiple preferences at once,
        see ``set_preferences`` method.

        Note: Even if this is a ``property``,
        to fetch the current preferences dict, you are required
        to call it like a bound method.

        Wrong::

            qb.preferences

        Right::

            qb.preferences()

        """
        prefs = self._get('app/preferences')

        class Proxy(Client):
            """
            Proxy class to to allow assignment of individual preferences.
            this class overrides some methods to ease things.

            Because of this, settings can be assigned like::

                In [5]: prefs = qb.preferences()

                In [6]: prefs['autorun_enabled']
                Out[6]: True

                In [7]: prefs['autorun_enabled'] = False

                In [8]: prefs['autorun_enabled']
                Out[8]: False

            """

            def __init__(self, url, prefs, auth, session):
                super(Proxy, self).__init__(url)
                self.prefs = prefs
                self._is_authenticated = auth
                self.session = session

            def __getitem__(self, key):
                return self.prefs[key]

            def __setitem__(self, key, value):
                kwargs = {key: value}
                return self.set_preferences(**kwargs)

            def __call__(self):
                return self.prefs

        return Proxy(self.url, prefs, self._is_authenticated, self.session)

    def set_preferences(self, **kwargs):
        """
        Set preferences of qBittorrent.
        Read all possible preferences @ https://git.io/fx2Y9

        :param kwargs: set preferences in kwargs form.
        """
        json_data = "json={}".format(json.dumps(kwargs))
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        return self._post('app/setPreferences', data=json_data,
                          headers=headers)

    @property
    def get_default_save_path(self):
        """
        Get Default save path of qBittorrent.
        """
        return self._get('app/defaultSavePath')


    """
    Log methods
    """


    def get_log(self, normal=True, info=True, warning=True, critical=True, last_known_id=-1):
        """
        Get log of qBittorrent
        
        :param normal: Include normal messages.
        :param info: Include info messages.
        :param warning: Include warning messages.
        :param critical: Include critical messages.
        :param last_known_id: Exclude messages with "message id" <= ``last_known_id``.
        """
        data = {'normal': normal, 'info': info, 'warning': warning, 'critical': critical, 'last_known_id': last_known_id}
        return self._post('log/main', data=data)

    def get_peer_log(self, last_known_id=-1):
        """
        Get peers log

        :param last_known_id: Exclude messages with "message id" <= ``last_known_id``.
        """
        data = {'last_known_id': last_known_id}
        return self._post('log/peers', data=data)


    """
    Sync methods
    """


    def get_sync_maindata(self, rid=0):
        """
        Sync the torrents by supplied LAST RESPONSE ID.
        Read more @ https://git.io/fxgB8

        :param rid: Response ID of last request.
        """
        return self._get('sync/maindata', params={'rid': rid})
    
    def get_sync_torrentPeers(self, hash, rid=0):
        """
        Sync a torrent by its has supplied LAST RESPONSE ID.
        Read more @ https://git.io/fxgBg

        :param hash: Hash of the torrent.
        :param rid: Response ID of last request.
        """
        return self._get('sync/torrentPeers', params={'hash': hash, 'rid': rid})

    
    """
    Transfer info methods
    """


    @property
    def global_transfer_info(self):
        """
        Get JSON data of the global transfer info of qBittorrent.
        """
        return self._get('transfer/info')

    @property
    def get_alternative_speed_status(self):
        """
        Get Alternative speed limits. (1/0)
        """
        return self._get('transfer/speedLimitsMode')

    def toggle_alternative_speed(self):
        """
        Toggle alternative speed limits.
        """
        return self._get('transfer/toggleSpeedLimitsMode')

    @property
    def get_global_download_limit(self):
        """
        Get global download speed limit.
        """
        return self._get('transfer/downloadLimit')

    def set_global_download_limit(self, limit):
        """
        Set global download speed limit.

        :param limit: Speed limit in bytes.
        """
        return self._post('transfer/setDownloadLimit', data={'limit': limit})

    @property
    def get_global_upload_limit(self):
        """
        Get global upload speed limit.
        """
        return self._get('transfer/uploadLimit')

    def set_global_upload_limit(self, limit):
        """
        Set global upload speed limit.

        :param limit: Speed limit in bytes.
        """
        return self._post('transfer/setUploadLimit', data={'limit': limit})


    """
    Torrent management methods
    """


    def torrents(self, **filters):
        """
        Returns a list of torrents matching the supplied filters.

        :param filter: Current status of the torrents.
        :param category: Fetch all torrents with the supplied label.
        :param sort: Sort torrents by.
        :param reverse: Enable reverse sorting.
        :param limit: Limit the number of torrents returned.
        :param offset: Set offset (if less than 0, offset from end).

        :return: list() of torrent with matching filter.
        """
        params = {}
        for name, value in filters.items():
            # make sure that old 'status' argument still works
            name = 'filter' if name == 'status' else name
            params[name] = value

        return self._get('torrents/info', params=params)

    def get_torrent(self, infohash):
        """
        Get details of the torrent.

        :param infohash: INFO HASH of the torrent.
        """
        return self._post('torrents/properties', data={'hash': infohash})

    def get_torrent_trackers(self, infohash):
        """
        Get trackers for the torrent.

        :param infohash: INFO HASH of the torrent.
        """
        return self._post('torrents/trackers', data={'hash': infohash})

    def get_torrent_webseeds(self, infohash):
        """
        Get webseeds for the torrent.

        :param infohash: INFO HASH of the torrent.
        """
        return self._post('torrents/webseeds', data={'hash': infohash})

    def get_torrent_files(self, infohash):
        """
        Get list of files for the torrent.

        :param infohash: INFO HASH of the torrent.
        """
        return self._post('torrents/files', data={'hash': infohash})

    def get_torrent_pieces_state(self, infohash):
        """
        Get pieces' state for the torrent.

        :param infohash: INFO HASH of the torrent.
        """
        return self._post('torrents/pieceStates', data={'hash': infohash})

    def get_torrent_pieces_hashes(self, infohash):
        """
        Get pieces' hash for the torrent.

        :param infohash: INFO HASH of the torrent.
        """
        return self._post('torrents/pieceHashes', data={'hash': infohash})
    
    def pause(self, infohash_list):
        """
        Pause one or multiple torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self._process_infohash_list(infohash_list)
        return self._post('torrents/pause', data=data)

    def pause_all(self):
        """
        Pause all torrents.
        """
        return self._post('torrents/pause', data={'hashes': 'all'})

    def resume(self, infohash_list):
        """
        Resume one or multiple paused torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self._process_infohash_list(infohash_list)
        return self._post('torrents/resume', data=data)

    def resume_all(self):
        """
        Resume all torrents.
        """
        return self._post('torrents/resume', data={'hashes': 'all'})
        
    def delete(self, infohash_list):
        """
        Delete torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self._process_infohash_list(infohash_list)
        data['deleteFiles'] = False
        return self._post('torrents/delete', data=data)

    def delete_permanently(self, infohash_list):
        """
        Permanently delete torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self._process_infohash_list(infohash_list)
        data['deleteFiles'] = True
        return self._post('torrents/delete', data=data)

    def recheck(self, infohash_list):
        """
        Recheck torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self._process_infohash_list(infohash_list)
        return self._post('torrents/recheck', data=data)
        
    def recheck_all(self):
        """
        Recheck all torrents.
        """
        return self._post('torrents/recheck', data={'hashes': 'all'})

    def reannounce(self, infohash_list):
        """
        Reannounce torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self._process_infohash_list(infohash_list)
        return self._post('torrents/reannounce', data=data)
        
    def reannounce_all(self):
        """
        Reannounce all torrents.
        """
        return self._post('torrents/reannounce', data={'hashes': 'all'})

    def download_from_link(self, link, **kwargs):
        """
        Download torrent using a link.

        :param link: URL Link or list of.
        :param savepath: Path to download the torrent.
        :param category: Label or Category of the torrent(s).

        :return: Empty JSON data.
        """
        # old:new format
        old_arg_map = {'save_path': 'savepath'}  # , 'label': 'category'}

        # convert old option names to new option names
        options = kwargs.copy()
        for old_arg, new_arg in old_arg_map.items():
            if options.get(old_arg) and not options.get(new_arg):
                options[new_arg] = options[old_arg]

        if type(link) is list:
            options['urls'] = "\n".join(link)
        else:
            options['urls'] = link

        # workaround to send multipart/formdata request
        # http://stackoverflow.com/a/23131823/4726598
        dummy_file = {'_dummy': (None, '_dummy')}

        return self._post('torrents/add', data=options, files=dummy_file)

    def download_from_file(self, file_buffer, **kwargs):
        """
        Download torrent using a file.

        :param file_buffer: Single file() buffer or list of.
        :param save_path: Path to download the torrent.
        :param label: Label of the torrent(s).

        :return: Empty JSON data.
        """
        if isinstance(file_buffer, list):
            torrent_files = {}
            for i, f in enumerate(file_buffer):
                torrent_files.update({'torrents%s' % i: f})
        else:
            torrent_files = {'torrents': file_buffer}

        data = kwargs.copy()

        if data.get('save_path'):
            data.update({'savepath': data['save_path']})
        return self._post('torrents/add', data=data, files=torrent_files)

    def add_trackers(self, infohash, trackers):
        """
        Add trackers to a torrent.

        :param infohash: INFO HASH of torrent.
        :param trackers: Trackers.
        """
        data = {'hash': infohash.lower(),
                'urls': trackers}
        return self._post('torrents/addTrackers', data=data)

    def increase_priority(self, infohash_list):
        """
        Increase priority of torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self._process_infohash_list(infohash_list)
        return self._post('torrents/increasePrio', data=data)

    def decrease_priority(self, infohash_list):
        """
        Decrease priority of torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self._process_infohash_list(infohash_list)
        return self._post('torrents/decreasePrio', data=data)

    def set_max_priority(self, infohash_list):
        """
        Set torrents to maximum priority level.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self._process_infohash_list(infohash_list)
        return self._post('torrents/topPrio', data=data)

    def set_min_priority(self, infohash_list):
        """
        Set torrents to minimum priority level.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self._process_infohash_list(infohash_list)
        return self._post('torrents/bottomPrio', data=data)

    def set_file_priority(self, infohash, file_id, priority):
        """
        Set file of a torrent to a supplied priority level.

        :param infohash: INFO HASH of torrent.
        :param file_id: ID of the file to set priority.
        :param priority: Priority level of the file.
        """
        if priority not in [0, 1, 2, 7]:
            raise ValueError("Invalid priority, refer WEB-UI docs for info.")
        elif not isinstance(file_id, int):
            raise TypeError("File ID must be an int")

        data = {'hash': infohash.lower(),
                'id': file_id,
                'priority': priority}

        return self._post('torrents/filePrio', data=data)        

    def get_torrent_download_limit(self, infohash_list):
        """
        Get download speed limit of the supplied torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self._process_infohash_list(infohash_list)
        return self._post('torrents/downloadLimit', data=data)

    def set_torrent_download_limit(self, infohash_list, limit):
        """
        Set download speed limit of the supplied torrents.

        :param infohash_list: Single or list() of infohashes.
        :param limit: Speed limit in bytes.
        """
        data = self._process_infohash_list(infohash_list)
        data.update({'limit': limit})
        return self._post('torrents/setDownloadLimit', data=data)

    def set_torrent_share_limit(self, infohash_list, ratioLimit=-2, seedingTimeLimit=-2):
        """
        Set share limit of the supplied torrents.

        :param infohash_list: Single or list() of infohashes.
        :param ratioLimit: Max ratio the torrent should be seeded until. -2 means the global limit, -1 means no limit.
        :param seedingTimeLimit: Max amount of time the torrent should be seeded. -2 means the global limit, -1 means no limit.
        """
        data = self._process_infohash_list(infohash_list)
        data.update({'ratioLimit': ratioLimit, 'seedingTimeLimit': seedingTimeLimit})
        return self._post('torrents/setShareLimits', data=data)

    def get_torrent_upload_limit(self, infohash_list):
        """
        Get upoload speed limit of the supplied torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self._process_infohash_list(infohash_list)
        return self._post('torrents/uploadLimit', data=data)

    def set_torrent_upload_limit(self, infohash_list, limit):
        """
        Set upload speed limit of the supplied torrents.

        :param infohash_list: Single or list() of infohashes.
        :param limit: Speed limit in bytes.
        """
        data = self._process_infohash_list(infohash_list)
        data.update({'limit': limit})
        return self._post('torrents/setUploadLimit', data=data)

    def set_location(self, infohash_list, location):
        """
        Set the location on multiple torrents.

        :param infohash_list: Single or list() of infohashes.
        :param location: Location to download the torrent to.
        """
        data = self._process_infohash_list(infohash_list)
        data.update({'location': location})
        return self._post('torrents/setLocation', data=data)

    def set_torrent_name(self, infohash, name):
        """
        Rename a torrent.

        :param infohash: Infohash of the torrent to rename.
        :param name: Name to rename the torrent to.
        """
        data = {'hash': infohash, 'name': name}
        return self._post('torrents/rename', data=data)

    def set_category(self, infohash_list, category):
        """
        Set the category on multiple torrents.

        :param infohash_list: Single or list() of infohashes.
        :param category: The torrent category to set.
        """
        data = self._process_infohash_list(infohash_list)
        data['category'] = category
        return self._post('torrents/setCategory', data=data)
    
    def add_category(self, category):
        """
        Add a new category.

        :param category: The name of the category.
        """
        return self._post('torrents/createCategory', data={'category': category})
    
    def edit_category(self, category, savePath):
        """
        Edit a category.

        :param category: The name of the category.
        :param savePath: Path to save downloaded torrents to.
        """
        data = {'category': category, 'savePath': savePath}
        return self._post('torrents/editCategory', data=data)
    
    def remove_category(self, category_list):
        """
        Remove one or more categories.

        :param category_list: List of categories to remove.
        """
        if isinstance(category_list, list):
            data = {'categories': '%0A'.join([h.lower() for h in category_list])}
        else:
            data = {'categories': category_list.lower()}
        return self._post('torrents/removeCategories', data=data)

    def set_automatic_torrent(self, infohash_list, enable):
        """
        Enable or disable automatic torrent management for one or multiple torrents.

        :param infohash_list: Single or list() of infohashes.
        :param enable: Enable or disable automatic torrent management.
        """
        data = self._process_infohash_list(infohash_list)
        data['enable'] = enable
        return self._post('torrents/setAutoManagement', data=data)

    def set_automatic_torrent_all(self, enable=False):
        """
        Enable or disable automatic torrent management for  all torrents.
        
        :param enable: Enable or disable automatic torrent management.
        """
        return self._post('torrents/setAutoManagement', data={'hashes': 'all', 'enable': enable})

    def toggle_sequential_download(self, infohash_list):
        """
        Toggle sequential download in supplied torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self._process_infohash_list(infohash_list)
        return self._post('torrents/toggleSequentialDownload', data=data)

    def toggle_first_last_piece_priority(self, infohash_list):
        """
        Toggle first/last piece priority of supplied torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self._process_infohash_list(infohash_list)
        return self._post('torrents/toggleFirstLastPiecePrio', data=data)

    def force_start(self, infohash_list, value=True):
        """
        Force start selected torrents.

        :param infohash_list: Single or list() of infohashes.
        :param value: Force start value (bool)
        """
        data = self._process_infohash_list(infohash_list)
        data.update({'value': json.dumps(value)})
        return self._post('torrents/setForceStart', data=data)

    def set_super_seeding(self, infohash_list, value):
        """
        Enable or disable super seeding for one or multiple torrents.

        :param infohash_list: Single or list() of infohashes.
        :param value: Enable or disable super seeding.
        """
        data = self._process_infohash_list(infohash_list)
        data['value'] = value
        return self._post('torrents/setSuperSeeding', data=data)

    def set_super_seeding_all(self, value=False):
        """
        Enable or disable super seeding for  all torrents.
        
        :param value: Enable or disable super seeding.
        """
        return self._post('torrents/setSuperSeeding', data={'hashes': 'all', 'value': value})
        
    @staticmethod
    def _process_infohash_list(infohash_list):
        """
        Method to convert the infohash_list to qBittorrent API friendly values.

        :param infohash_list: List of infohash.
        """
        if isinstance(infohash_list, list):
            data = {'hashes': '|'.join([h.lower() for h in infohash_list])}
        else:
            data = {'hashes': infohash_list.lower()}
        return data

    """
    RSS Methods
    """

    def add_folder(self, path):
        """
        Add a new rss feed folder.
        
        :param path: Name of the rss folder to add.
        """
        return self._post('rss/addFolder', data={'path': path})

    def add_feed(self, url, path):
        """
        Add new RSS feed.
        
        :param url: Url of the RSS feed to add.
        :param path: Name of the RSS feed.
        """
        data = {'url': url, 'path': path}
        return self._post('rss/addFeed', data=data)

    def remove_item(self, path):
        """
        Remove a rss feed or folder.
        
        :param path: Name of the rss folder to remove.
        """
        return self._post('rss/addFeed', data={'path': path})

    def get_item(self, withData=False):
        """
        Get items of the existing RSS feeds.

        :param withData: True if current feed data is needed.
        """
        return self._get('rss/items', data={'withData': withData})

    def set_rule(self, ruleName, ruleDef):
        """
        Set a new auto-downloading rule.

        :param ruleName: Rule name.
        :param ruleDef: JSON encoded rule definition.
        
        See example @ https://git.io/fxhLq
        """
        data = {'ruleName': ruleName, 'ruleDef': ruleDef}
        return self._post('rss/setRule', data=data)

    def rename_rule(self, ruleName, newRuleName):
        """
        Rename an existing auto-downloading rule.

        :param ruleName: Rule name to rename.
        :param newRuleName: New rule name to rename to.
        """
        data = {'ruleName': ruleName, 'newRuleName': newRuleName}
        return self._post('rss/renameRule', data=data)

    def remove_rule(self, ruleName):
        """
        Remove an existing auto-downloading rule.

        :param ruleName: Rule name to remove.
        """
        return self._post('rss/removeRule', data={'ruleName': ruleName})

    def get_rules(self):
        """
        Returns all auto-downloading rules in JSON format.
        """
        return self._get('rss/rules')
