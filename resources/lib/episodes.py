import xbmc
import xbmcgui
import xbmcplugin
import os
import sys
import json
import urllib
import cache
import common
import sickbeard
import TvdbApi


pluginID = 'plugin.video.sickrage'

# Initialize Sickbeard Class
Sickbeard = sickbeard.SB()


# Get episodes for the selected show and season.
def GetSeasonEpisodes(tvdbid, season):
    list = []
    season_episodes = Sickbeard.GetSeasonEpisodeList(tvdbid, season)
    if not season_episodes:
        exit()
    temp = season_episodes.keys()
    temp = sorted(temp)
    for each in temp:
      list.append([each, season_episodes[each]['name'], season_episodes[each]['status'], season_episodes[each]['airdate'], tvdbid, season])
    return list


# Add directory items for each episode.
def menu(tvdbid, show_name, season):
    list = GetSeasonEpisodes(tvdbid, season)
    total_items = len(list)
    season_numbers = []
    for ep_number, name, status, airdate, ep_tvdbid, ep_season in list:
        season_numbers.append(str(ep_number))
        season_status_args = ", " + ep_tvdbid + ", " + ep_season + ", " + "|".join(season_numbers)
        episode_status_args = ", " + ep_tvdbid + ", " + ep_season + ", " + ep_number

        context_items = []
        context_items.append(('Show Info', 'XBMC.Action(Info)'))
        context_items.append(('Open Show Folder', 'XBMC.RunPlugin(plugin://{0}?mode={1}&tvdb_id={2}&show_name={3})'.format(pluginID, 15, tvdbid, urllib.quote_plus(show_name.encode("utf-8")))))
        if xbmc.getCondVisibility('System.HasAddon(script.extendedinfo)'):
            context_items.append(('ExtendedInfo', 'XBMC.RunScript(script.extendedinfo, info=extendedtvinfo, tvdb_id={0})'.format(tvdbid)))
        context_items.append(('Set Episode Status', 'XBMC.RunScript(special://home/addons/{0}/resources/lib/setstatus.py{1})'.format(pluginID, episode_status_args)))
        context_items.append(('Set Season Status', 'XBMC.RunScript(special://home/addons/{0}/resources/lib/setstatus.py{1})'.format(pluginID, season_status_args)))
        context_items.append(('Download Episode', 'XBMC.RunScript(special://home/addons/{0}/resources/lib/manualsearch.py{1})'.format(pluginID, episode_status_args)))
        context_items.append(('Update Cache from TVdb', 'XBMC.RunScript(special://home/addons/{0}/resources/lib/cache.py, {1}, {2}, {3})'.format(pluginID, tvdbid, season, ep_number)))
        context_items.append(('Refresh List', 'XBMC.Container.Refresh'))
        context_items.append(('Go Back', 'XBMC.Action(back)'))

        thumbnail_path = Sickbeard.GetShowPoster(tvdbid)
        fanart_path = Sickbeard.GetShowFanArt(tvdbid)
        banner_path = Sickbeard.GetShowBanner(tvdbid)
        addDirectory(show_name, season, ep_number, name, status, airdate, tvdbid, thumbnail_path, fanart_path, banner_path, total_items, context_items)

    xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE)
    xbmcplugin.setContent(handle=int(sys.argv[1]), content='tvshows')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))
    common.CreateNotification(header='Show List', message=str(total_items)+' Shows in list', icon=xbmcgui.NOTIFICATION_INFO, time=3000, sound=False)


def addDirectory(show_name, season, episode, name, status, airdate, tvdbid, thumbnail_path, fanart_path, banner_path, total_items, context_items):
    return_url = sys.argv[0]+"?tvdb_id="+urllib.quote_plus(str(tvdbid))+"&mode=6&show_name="+urllib.quote_plus(show_name.encode( "utf-8" ))
    if (airdate != ''):
        aired = '(Aired ' + airdate + ')   '
    else:
        aired = ''
    name = "[COLOR gold]" + str(season) + "x" + str(episode) + ". "+ name + "[/COLOR]   " + aired + status
    list_item = xbmcgui.ListItem(name)
    list_item.setArt({'icon': thumbnail_path, 'thumb': thumbnail_path, 'poster': thumbnail_path, 'fanart': fanart_path, 'banner': banner_path, 'clearart': '', 'clearlogo': '', 'landscape': ''})
    list_item.setProperty('LibraryHasMovie', '0')  # Removes the "Play" button from the video info screen, and replaces it with "Browse".
    meta = {}
    try:
        # Load and parse meta data.
        if not os.path.exists(cache.ep_cache_dir):
            os.makedirs(cache.ep_cache_dir)
        json_file = os.path.join(cache.ep_cache_dir, tvdbid + '-' + str(season) + '-' + str(episode) + '.json')
        if os.path.isfile(json_file):
            # Load cached tvdb episode json file.
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
            except Exception, e:
                print e
        else:
            data = TvdbApi.GetMetaDataDict(tvdbid, int(season), int(episode), '', log=None)
            # Save cached tvdb episode json file.
            try:
                with open(json_file, 'w') as f:
                    json.dump(data, f, sort_keys=True, indent=4)
            except Exception, e:
                print e
        meta['tvshowtitle'] = TvdbApi.getFromDict(data, ['Show', 'seriesName'], show_name)
        meta['sorttitle'] = name
        meta['title'] = name # This is what is displayed at the top of the video dialog window.
        meta['originaltitle'] = TvdbApi.getFromDict(data, ['Details', 'episodeName'], name)
        meta['season'] = int(season)
        meta['episode'] = int(episode)
        meta['tvdb_id'] = str(tvdbid)
        meta['imdbnumber'] = TvdbApi.getFromDict(data, ['Show', 'imdbId'], '')
        meta['overlay'] = 6
        meta['plot'] = TvdbApi.getFromDict(data, ['Details', 'overview'], '')
        list_item.setRating('tvdb', TvdbApi.getFromDict(data, ['Show', 'siteRating'], 0), TvdbApi.getFromDict(data, ['Show', 'siteRatingCount'], 0), True)
        meta['premiered'] = TvdbApi.getFromDict(data, ['Details', 'firstAired'], airdate)
        meta['aired'] = meta['premiered']
        meta['dateadded'] = meta['premiered']
        # Date for sorting must be in Kodi format dd.mm.yyyy
        meta['date'] = meta['premiered'][8:10] + '.' + meta['premiered'][5:7] + '.' + meta['premiered'][0:4]
        meta['duration'] = TvdbApi.getFromDict(data, ['Show', 'runtime'], 0)    # Minutes.
        meta['genre'] = ' / '.join(TvdbApi.getFromDict(data, ['Show', 'genre'], ''))
        meta['writer'] = ', '.join(TvdbApi.getFromDict(data, ['Details', 'writers'], ''))
        meta['director'] = ', '.join(TvdbApi.getFromDict(data, ['Details', 'directors'], ''))
        meta['studio'] = TvdbApi.getFromDict(data, ['Show', 'network'], '')
        meta['mpaa'] = TvdbApi.getFromDict(data, ['Show', 'rating'], '')
        meta['episode_id'] = TvdbApi.getFromDict(data, ['Details', 'id'], '')
        meta['year'] = TvdbApi.getFromDict(data, ['Show', 'firstAired'], '')[:4]
        meta['status'] = TvdbApi.getFromDict(data, ['Show', 'status'], '')
        #meta['cast'] = []
        #actors = [{'name': 'Tom Cruise', 'role': 'Himself', 'thumbnail': ''}, {'name': 'Actor 2', 'role': 'role 2'}]
        actors = data.get('Actors', [])
        actors = TvdbApi.CacheActorImages(actors, cache.actor_cache_dir)
        for value in TvdbApi.getFromDict(data, ['Details', 'guestStars'], ''):
            actors.append(dict({'name': value, 'role': 'Guest Star'}))
        if actors:
            list_item.setCast(actors)
    except:
        meta['tvdb_id'] = str(tvdbid)
        meta['tvshowtitle'] = show_name
        meta['title'] = name
        meta['season'] = int(season)
        meta['episode'] = int(episode)
    list_item.setInfo(type="Video", infoLabels=meta)
    list_item.addContextMenuItems(context_items, replaceItems = True)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=return_url, listitem=list_item, isFolder=False, totalItems=total_items)

