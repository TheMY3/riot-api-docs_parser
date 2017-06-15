import os
import sys
from bs4 import BeautifulSoup

# Console output
orig_stdout = sys.stdout
sys.stdout = open('log.txt', 'w')

with open("input/input.html") as f:
    content = f.readlines()
content = ''.join([str(line) for line in content])


def cleandir(path):
    try:
        for entry in os.listdir(path):
            newpath = path + "/" + entry
            if os.path.isdir(newpath):
                cleandir(newpath)
                os.removedirs(newpath)
            else:
                os.remove(newpath)
    except PermissionError:
        pass

outputDir = os.getcwd() + "/output/"
cleandir(outputDir)

resourceIgnored = [
    # Champion v1.2
    1206,
    # ChampionMastery
    1091,
    # CurrentGame v1.0
    976,
    # Featured Games v1.0
    977,
    # Game v1.3
    1207,
    # League v2.5
    1215,
    # LoL Static Data v1.2
    1055,
    # LoL Status v1.0
    1085,
    # Match v2.2
    1224,
    # MatchList v2.2
    1223,
    # Runes Masteries v1.4
    1222,
    # Stats v1.3
    1209,
    # Summoner v1.4
    1221,
    # Tournament Provider v1
    1057,
    # Tournament Stub v1
    1090,
]
resourceMapping = {
    # lol-static-data
    "1351": {
        "classNamePrepend": "Static",
        "classDir": "StaticData",
        "classPackage": "RiotAPI\Objects\StaticData",
    }
}
resources = {}

classes = {}
classesIterable = {
    # static-data
    "StaticChampionListDto": "data",
    "StaticItemListDto": "data",
    "StaticMapDataDto": "data",
    "StaticMasteryListDto": "data",
    "StaticMasteryTreeListDto": "masteryTreeItems",
    "StaticRuneListDto": "data",
    "StaticSummonerSpellListDto": "data",
    # other
    "ChampionListDto": "champions",
    "FeaturedGames": "gameList",
    "Frame": "events",
    "LeagueDto": "entries",
    "LobbyEventDtoWrapper": "eventList",
    "MasteryPageDto": "masteries",
    "MasteryPagesDto": "pages",
    "MatchList": "matches",
    "PlayerStatsSummaryListDto": "playerStatSummaries",
    "RankedStatsDto": "champions",
    "RecentGamesDto": "games",
    "RunePageDto": "slots",
    "RunePagesDto": "pages",
    "Service": "incidents",
    "ShardStatus": "services",
    "Timeline": "frames",
}

apiMethods = []

print("Parsing resources and endpoints\n====")
soup = BeautifulSoup(content, 'lxml')
for data_resource in soup.find_all('li'):
    try:
        if 'resource' not in data_resource['class']:
            # class does not match
            continue

        data_resource['id'].index('resource_')
    except KeyError:
        # No class or id
        continue
    except ValueError:
        # Invalid id
        continue

    heading = data_resource.find('a').find('span').text
    link = data_resource.find('a')['href']

    try:
        version = heading[heading.rindex('-') + 1:]
        heading = heading[:heading.rindex('-')]
    except ValueError:
        version = "unknown"

    r = {
        "id": "",
        "name": heading,
        "version": version,
        "link": link,
        "ignored": False,
        "endpoints": []
    }
    print("Parsed resource {0} ({1}) [{2}]".format(heading, version, link), end='')

    for data_endpoint in data_resource.find_all('ul'):
        try:
            if 'endpoints' not in data_endpoint['class']:
                # class does not match
                continue

            i = data_endpoint['id'].index('_endpoint_list')
        except KeyError:
            # No class or id
            continue
        except ValueError:
            # Invalid id
            continue

        r['id'] = resourceId = data_endpoint['id'][:i]
        if int(resourceId) in resourceIgnored:
            print(" (but ignored)")
            r["ignored"] = True
        else:
            print()

        for data_operation in data_endpoint.find_all('li'):
            try:
                if 'operation' not in data_operation['class']:
                    # class does not match
                    continue

                # data_operation['id'].index(resourceId + '_')
            except KeyError:
                # No class or id
                continue
            except ValueError:
                # No class or id
                continue

            endpointId = data_operation['id'][1:]

            # Creating API method list from not ignored endpoints
            if r["ignored"] is not True:
                methodName = endpointId

                # If Tournament Stub v3
                if resourceId == "1242":
                    methodName = methodName + "_STUB"

                apiMethods.append(methodName)

            for data_objectClass in data_operation.find_all('div'):
                try:
                    if 'response_body' not in data_objectClass['class']:
                        # class does not match
                        continue
                except KeyError:
                    # No class or id
                    continue

                endpointLink = "unknown"
                for a in data_endpoint.find_all('a'):
                    try:
                        if a['href'].index(link + "/"):
                            # class does not match
                            continue
                    except ValueError:
                        # No class or id
                        continue

                    endpointLink = a['href']
                    break

                endpointData = {
                    "id": endpointId,
                    "resourceId": resourceId,
                    "link": endpointLink,
                    "html": data_objectClass
                }
                r['endpoints'].append(endpointData)

            print("\tParsed endpoint {0} [{1}]".format(endpointId, endpointLink))
        print()
    try:
        resources[r['name']] = r
    except AttributeError:
        pass

print("\nMapping classes\n====")
for resourceName in resources:
    resource = resources[resourceName]
    if resource["ignored"]:
        continue

    endpointsPrinted = []
    print("Mapping classes for resource {1} - {0}".format(resource["name"], resource["id"]))
    for endpoint in resource['endpoints']:
        if endpoint["id"] not in endpointsPrinted:
            print("\tMapping classes in endpoint {0}".format(endpoint["id"]))
            endpointsPrinted.append(endpoint["id"])

        data_objectClass = endpoint['html']
        # head = data_objectClass.find('h5').findParent("div").text
        text = data_objectClass.text

        try:
            className = text[:text.index(' - ')].strip()
            classDesc = text[text.index(' - ') + 3:text.find("Name\nData Type\nDescription")].strip()
        except ValueError:
            className = text
            classDesc = ""

        try:
            if className.index(' '):
                continue
        except ValueError:
            pass

        try:
            if className.index(':'):
                continue
        except ValueError:
            pass

        try:
            i = className.index('DTO')
            className = className[:i] + "Dto" + className[i + 3:]
        except ValueError:
            pass

        try:
            mapping = resourceMapping[resource['id']]
            classId = mapping["classNamePrepend"] + className
            print("\t\tCustom mapping {0:21} => {2}\{1}".format(className, classId, mapping["classPackage"]))
            try:
                c = classes[classId]
            except KeyError:
                c = {
                    "className": mapping["classNamePrepend"] + className,
                    "classNamePrepend": mapping["classNamePrepend"],
                    "classDesc": classDesc,
                    "classDir": mapping["classDir"],
                    "classPackage": mapping["classPackage"],
                    "classExtends": {
                        "className": "ApiObject",
                        "classPackage": "RiotAPI\Objects",
                    },
                    "resources": [],
                    "endpoints": {},
                    "properties": [],
                }
        except KeyError:
            try:
                classId = className
                c = classes[classId]
            except KeyError:
                c = {
                    "className": className,
                    "classNamePrepend": "",
                    "classDesc": classDesc,
                    "classDir": "",
                    "classPackage": "RiotAPI\Objects",
                    "classExtends": {
                        "className": "ApiObject",
                        "classPackage": "RiotAPI\Objects",
                    },
                    "resources": [],
                    "endpoints": {},
                    "properties": [],
                }

        try:
            if resource not in c['resources']:
                c['resources'].append(resource)

            if endpoint not in c['endpoints'][resource['name']]:
                c['endpoints'][resource['name']].append(endpoint)
        except KeyError:
            c['endpoints'][resource['name']] = []
            c['endpoints'][resource['name']].append(endpoint)

        for tr in data_objectClass.find_all('tr'):
            varInfo = tr.find_all('td')
            if not len(varInfo):
                continue

            before = ""
            varName = str(varInfo[0].text).strip()
            varNameAfter = ""
            dataType = str(varInfo[1].text).strip()

            desc = str(varInfo[2].text).strip()
            if len(desc) != 0:
                if desc[len(desc)-1:] != '.':
                    desc += '.'

                charCount = 0
                descSplit = desc.split()
                for idx, word in enumerate(descSplit):
                    charCount += len(word) + 1
                    if charCount > 75:
                        descSplit[idx] = "\n\t * " + word
                        charCount = 0

                desc = ' '.join(descSplit)

            try:
                dataType.index('Map[')
                i = dataType.index(', ') + 2
                dataType = dataType[i:-1] + "[]"
            except ValueError:
                pass

            try:
                dataType.index('List[')
                i = dataType.index('[') + 1
                dataType = dataType[i:-1] + "[]"
            except ValueError:
                pass

            try:
                dataType.index('Set[')
                i = dataType.index('[') + 1
                dataType = dataType[i:-1] + "[]"
            except ValueError:
                pass

            dataTypeAppend = ""
            try:
                dataType.index('[]')
                dataType = dataType[:-2]
                dataTypeAppend = "[]"
            except ValueError:
                pass

            if dataType in ['long']:
                dataType = 'int'

            if dataType in ['boolean']:
                dataType = 'bool'

            stdDataTypes = ['integer', 'int', 'string', 'bool', 'boolean', 'double', 'float', 'array']
            if dataType not in stdDataTypes:
                dataType = c["classNamePrepend"] + dataType

            dataType += dataTypeAppend

            p = {
                "name": varName,
                "dataType": dataType,
                "desc": desc,
            }

            propDuplicity = False
            for prop in c['properties']:
                if prop['name'] == p['name']:
                    propDuplicity = True

            if not propDuplicity:
                c['properties'].append(p)

        classes[classId] = c
    print()

print("\nCreating classes\n====")
for className in classes:
    c = classes[className]
    if not c['properties']:
        continue

    classAnnotation = ""
    if len(c['classDesc']):
        classAnnotation += "\n * " + c['classDesc']

    classAnnotation += "\n *\n * Used in:"
    for resource in c['resources']:
        classAnnotation += "\n *   " + resource['name'] + " (" + resource['version'] + ")"
        for endpoint in c['endpoints'][resource['name']]:
            classAnnotation += "\n *     @link " + endpoint['link']

    if c['className'] in classesIterable:
        classAnnotation += "\n *\n * @iterable $" + classesIterable[c['className']]
        c['classExtends']['className'] = "ApiObjectIterable"

    classUses = ""
    if c['classPackage'] != c['classExtends']['classPackage']:
        classUses += "\nuse " + c['classExtends']['classPackage'] + "\\" + c['classExtends']['className'] + ";\n"

    properties = ""
    for prop in c['properties']:
        if len(prop['desc']):
            properties += "\n\t/**\n\t *   " + prop["desc"] + "\n\t *"
            properties += "\n\t * @var " + prop['dataType'] + " $" + prop['name'] + "\n\t */"
        else:
            properties += "\n\t/** @var " + prop['dataType'] + " $" + prop['name'] + " */"
        properties += "\n\tpublic $" + prop['name'] + ";\n"

    classDir = ""
    if len(c['classDir']):
        classDir = c['classDir'] + "/"

    if not os.path.exists('output/' + classDir):
        os.makedirs('output/' + classDir)

    with open('output/{0}{1}.php'.format(classDir, className), 'w', encoding='utf8') as file_:
        template = '''<?php

/**
 * Copyright (C) 2016  Daniel Dolejška
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

namespace ''' + c['classPackage'] + ''';
''' + classUses + '''

/**
 *   Class ''' + c['className'] + classAnnotation + '''
 *
 * @package ''' + c['classPackage'] + '''
 */
class ''' + c['className'] + ''' extends ''' + c['classExtends']['className'] + '''
{''' + properties + '''}
'''
        file_.write(template)
    print("Saved class {0:33}: {1}{0}.php".format(className, classDir))

endpointCount = 0
for resName in resources:
    r = resources[resName]
    endpointCount += len(r['endpoints'])
print("\nSaved " + str(len(classes)) + " classes from "
      + str(endpointCount) + " endpoints in " + str(len(resources))+ " resources\n")
# m = re.search('<div class="block response_body">')


print("\nParsed API methods (endpoints)\n====")
for method in apiMethods:
    print(method)

sys.stdout.close()
orig_stdout.close()