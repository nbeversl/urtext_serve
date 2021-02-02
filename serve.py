from flask import Flask
from flask import request
import os
import json
from urtext.project_list import ProjectList
import time
import datetime
import sys
from urtext.project import soft_match_compact_node

EMPTY = json.dumps({'':''})

path = sys.argv[1]
if not os.path.exists(path):
    print('Path does not exist')
    sys.exit()

app = Flask(__name__)

project_list = ProjectList(path) 
if len(project_list.projects) == 0:
    print('No Urtext projects found here')
    sys.exit()

@app.route('/')
def hello_world():
    return json.dumps({
        'title' : project_list.current_project.title,
        'path' : project_list.current_project.path,
        'nav_current' : project_list.nav_current(),
        })

@app.route('/projects', methods=['GET', 'POST'])
def show_projects():
    s = { 'projects' : []}
    for p in project_list.projects: 
        s['projects'].append(p.title)
    return json.dumps(s)

@app.route('/set-project', methods=['GET', 'POST'])
def set_project():
    d = request.form.to_dict()
    project_list.set_current_project(d['title'])
    while not project_list.current_project.compiled:
        time.sleep(1)
    filename, node_position = project_list.current_project.get_file_and_position(
        project_list.nav_current())
    if not filename:
        print('File not found for node')
        return EMPTY        
    return json.dumps({
        'title' : project_list.current_project.title,
        'path' : project_list.current_project.path,
        'nav_current' : project_list.nav_current(),
        'filename' : os.path.join(project_list.current_project.path, filename),
        'position': node_position,
        'current_project' : project_list.current_project.title,
        })

@app.route('/home', methods=['GET', 'POST'])
def get_home():
    d = request.form.to_dict()
    if project_list.set_current_project(d['project']):
    
        node_id = project_list.current_project.get_home()
        project_list.nav_new(node_id)
        filename, node_position = project_list.current_project.get_file_and_position(
            project_list.nav_current())
        return json.dumps({
            'title' : project_list.current_project.title,
            'path' : project_list.current_project.path,
            'nav_current' : project_list.nav_current(),
            'filename' : os.path.join(project_list.current_project.path, filename),
            'position': node_position,
            'current_project' : project_list.current_project.title,
            })
    return EMPTY

@app.route('/get-link-set-project', methods=['GET', 'POST'])
def get_link_and_set_project():
    d = request.form.to_dict()
    link = project_list.get_link_and_set_project(d['line'], position=int(d['column']))
    if link == None:
        if not project_list.current_project.compiled:
           print("Project is still compiling")
        else:
            print(project_list.current_project)
            print(link)
            print('NO LINK') 
        return json.dumps({
            'title' : project_list.current_project.title,
            'path' : project_list.current_project.path,
            'link_kind' : 'NONE',
            'current_project' : project_list.current_project.title,
            })
    kind = link[0]
    response = {
        'title' : project_list.current_project.title,
        'path' : project_list.current_project.path,
        'link_kind' : kind,
        'link' : link[1],
        'nav_current' : project_list.nav_current()
        }
    if kind == 'NODE':
        project_list.nav_new(link[1])
        filename, node_position = project_list.current_project.get_file_and_position(
            project_list.nav_current())
        response['filename'] = os.path.join(project_list.current_project.path, filename)
        response['position'] = node_position

    return json.dumps(response)

@app.route('/tag-from-other', methods=['GET', 'POST'])
def tag_from_other():
    d = request.form.to_dict()
    link = project_list.get_link_and_set_project(d['line'], position=int(d['column']))

    if link[0] == 'NODE':
        project_list.current_project.tag_other_node(link[1])
    return json.dumps({'':''})

@app.route('/nav-forward', methods=['GET', 'POST'])
def nav_forward():
    next_node = project_list.nav_advance()
    filename, node_position = project_list.current_project.get_file_and_position(next_node)
    if next_node:
        return json.dumps({
            'title' : project_list.current_project.title,
            'path' : project_list.current_project.path,
            'nav_current' : project_list.nav_current(),
            'filename' : os.path.join(project_list.current_project.path, filename),
            'position': node_position,
            'current_project' : project_list.current_project.title,
            })
    return json.dumps({
        'title' : project_list.current_project.title,
        'path' : project_list.current_project.path,
        'nav_current' : 'NONE',
        })

@app.route('/nav-back', methods=['GET', 'POST'])
def nav_back():
    last_node = project_list.nav_reverse()
    if not last_node:
        return json.dumps({
                'title' : project_list.current_project.title,
                'path' : project_list.current_project.path,
                'nav_current' : 'NONE'
            })
    filename, node_position = project_list.current_project.get_file_and_position(last_node)
    return json.dumps({
        'title' : project_list.current_project.title,
        'path' : project_list.current_project.path,
        'nav_current' : project_list.nav_current(),
        'filename' : os.path.join(project_list.current_project.path, filename),
        'position': node_position,
        'current_project' : project_list.current_project.title,

        })

@app.route('/nav', methods=['GET', 'POST'])
def nav():
    d = request.form.to_dict()
    project_list.nav_new(d['node'])
    return json.dumps({
        'title' : project_list.current_project.title,
        'path' : project_list.current_project.path,
        'nav_current' : project_list.nav_current(),
        })

@app.route('/modified', methods=['GET', 'POST'])
def modified():
    d = request.form.to_dict()
    future = project_list.on_modified(d['filename'])
    if future and project_list.current_project.is_async:
        new_filename = future.result()
    elif not project_list.current_project.is_async:
        new_filename = future
    else:
        new_filename = os.path.basename(d['filename'])

    return json.dumps({
        'title' : project_list.current_project.title,
        'path' : project_list.current_project.path,
        'nav_current' : project_list.nav_current(),
        'filename' : new_filename,
        'completions': project_list.get_all_meta_pairs(),
        'titles' : project_list.current_project.title_completions
        })

@app.route('/nodes', methods=['GET', 'POST'])
def nodes():
    d = request.form.to_dict()
    project_list.set_current_project(d['project'])
    if 'nodes' not in d or not d['nodes']:
        requested_nodes = project_list.current_project.all_nodes()
    else:
        requested_nodes = d['nodes']
        requested_nodes = sorted(requested_nodes, 
            key=lambda nid: project_list.current_project.nodes[nid].date(), 
            reverse=True)
        
    r = { 'current_project' : project_list.current_project.title,
        'nodes' : [] }

    for n in requested_nodes:
        this_node = {}

        if project_list.current_project.nodes[n].title.strip() == '':
            this_node['title'] = '(no title)'
        else:
            this_node['title'] = project_list.current_project.nodes[n].title
        this_node['date'] = str(project_list.current_project.nodes[n].date())
        this_node['position'] = project_list.current_project.nodes[n].ranges[0][0]
        this_node['id'] = project_list.current_project.nodes[n].id
        this_node['project_title'] = project_list.current_project.title        
        this_node['filename'] = os.path.join(project_list.current_project.path, project_list.current_project.nodes[n].filename)
        r['nodes'].append(this_node)
    return json.dumps(r)

@app.route('/filename-from-link', methods=['GET', 'POST'])
def filename():
    d = request.form.to_dict()
    
    return json.dumps({
        'title' : project_list.current_project.title,
        'path' : project_list.current_project.path,
        'filename': os.path.join(project_list.current_project.path, project_list.current_project.get_file_name(d['link'])),
        'position' : project_list.current_project.nodes[d['link']].ranges[0][0]
        })

@app.route('/new-node', methods=['GET', 'POST'])
def new_node():
    new_node = project_list.current_project.new_file_node()
    project_list.nav_new(new_node['id'])        
    return json.dumps({
        'title' : project_list.current_project.title,
        'path' : project_list.current_project.path,
        'filename': os.path.join(project_list.current_project.path, new_node['filename']),
        'id' : new_node['id'],
        })

@app.route('/delete-file', methods=['GET', 'POST'])
def delete_file():
    d = request.form.to_dict()
    project_list.delete_file(d['filename']) 
    return json.dumps({
        'title' : project_list.current_project.title,
        'path' : project_list.current_project.path,
        })

@app.route('/backlinks', methods=['GET', 'POST'])
def backlinks():
    d = request.form.to_dict()
    backlinks = project_list.current_project.get_links_to(d['id'])

    return json.dumps({
        'title' : project_list.current_project.title,
        'path' : project_list.current_project.path,
        'backlinks' : backlinks,
        })

@app.route('/forward-links', methods=['GET', 'POST'])
def forward_links():
    d = request.form.to_dict()

    forward_links = project_list.current_project.get_links_to(d['id'])

    return json.dumps({
        'title' : project_list.current_project.title,
        'path' : project_list.current_project.path,
        'forward-links' : forward_links,
        })


@app.route('/id-from-position', methods=['GET', 'POST'])
def id_from_position():
    d = request.form.to_dict()
    node_id = project_list.current_project.get_node_id_from_position(d['filename'], int(d['position']))

    return json.dumps({
        'title' : project_list.current_project.title,
        'path' : project_list.current_project.path,
        'id' : node_id,
        })

@app.route('/move-file', methods=['GET', 'POST'])
def move_file():
    d = request.form.to_dict()
    replace_links = True if d['replace_links'] == 'True' else False
    success = project_list.move_file(d['filename'], d['new_project'], replace_links)
    last_node = project_list.nav_reverse()
    if last_node:
        filename = os.path.join(project_list.current_project.path, project_list.current_project.nodes[last_node].filename)
    else:
        filename = ''
        last_node = ''

    return json.dumps({
        'success' : str(success),
        'last_node' : last_node,
        'filename' : filename
        })


@app.route('/snapshot', methods=['GET', 'POST'])
def snapshot():
    d = request.form.to_dict()
    project = project_list.get_project(d['project'])
    if project:
        project.snapshot_diff(d['filename'], d['contents'])
        print('SNAPSHOT taken : '+ d['filename'] )
        return json.dumps({
            'success' : 'True',
            })
    return json.dumps({
            'success' : 'False',
            })

@app.route('/add-inline-node', methods=['GET', 'POST'])
def new_inline_node():
    d = request.form.to_dict()
    
    new_node = project_list.current_project.new_inline_node(contents=d['contents'])
    return json.dumps({
            'contents' : new_node['contents'],
            'id':new_node['id']
            })


@app.route('/rename-file', methods=['GET', 'POST'])
def rename_file():
    d = request.form.to_dict()
    renamed_files = project_list.current_project.rename_file_nodes(os.path.basename(d['old_filename']))
    return json.dumps({
            'new-filename' : renamed_files[d['old_filename']],
            })

@app.route('/get-link-to-node', methods=['GET', 'POST'])
def get_link_to_node():
    d = request.form.to_dict()
    if 'include_project' not in d:
        d['include_project'] = False
    include_project = True if d['include_project'] == 'True' else False
    link = project_list.build_contextual_link(
            d['node_id'],
            project_title=d['project'],
            include_project = include_project)    

    return json.dumps({
            'link' : link,
            })

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    return json.dumps({
        'project' : project_list.current_project.title,
        'settings' : project_list.current_project.settings,})


@app.route('/timestamp', methods=['GET', 'POST'])
def timestamp():
    datestamp = project_list.current_project.timestamp(datetime.datetime.now())
    return json.dumps({
        'timestamp' : datestamp})

@app.route('/consolidate-metadata', methods=['GET', 'POST'])
def consolidate_metadata():
    d = request.form.to_dict()
    if 'one_line' not in d:
        d['one_line'] = False
    project_list.current_project.consolidate_metadata(d['node-id'], 
        one_line=True if d['one_line'] == 'True' else False)

    return json.dumps({'' : ''})

@app.route('/reindex', methods=['GET', 'POST'])
def reindex():
    d = request.form.to_dict()
    project = project_list.get_project(d['project'])
    renamed_files = {}
    if project:
        renamed_files = project_list.current_project.reindex_files()
        renamed_files = renamed_files.result()
    return json.dumps({
        'renamed-files':renamed_files
        })

@app.route('/next-id', methods=['GET', 'POST'])
def next_id():
    d = request.form.to_dict()
    project_list.set_current_project(d['project'])
    node_id = project_list.current_project.next_index()
    return json.dumps({
        'node_id': node_id
        })
       

@app.route('/get-log-node', methods=['GET', 'POST'])
def get_log_node():
    d = request.form.to_dict()
    project_list.set_current_project(d['project'])
    log_id = project_list.current_project.get_log_node()

    return json.dumps({
        'node_id': log_id,
        'filename' : project_list.current_project.nodes[log_id].filename,
        'position' : project_list.current_project.nodes[log_id].ranges[0][0],
        })

@app.route('/compact-node', methods=['GET', 'POST'])
def compact_node():
    d = request.form.to_dict()
    project_list.set_current_project(d['project'])
    
    # determining whether this is already a compact node has to be done in a "soft" way
    # since the file may not be saved between request

    if soft_match_compact_node(d['selection']):
        # If it is already a compact node, make a new one on the next line down.
        replace = False
        contents = project_list.current_project.add_compact_node()
    else:
        # If it is not a compact node, make it one and add an ID
        replace = True
        contents = project_list.current_project.add_compact_node(contents=d['selection'])

    return json.dumps({
        'replace' : replace,
        'contents' : contents        
        })

@app.route('/pop-node', methods=['GET', 'POST'])
def pop_node():
    d = request.form.to_dict()
    project_list.set_current_project(d['project'])
    project_list.current_project.pop_node(filename=d['filename'], position=int(d['position']))
    return EMPTY

@app.route('/pull-node', methods=['GET', 'POST'])
def pull_node():
    d = request.form.to_dict()
    project_list.set_current_project(d['project'])
    project_list.current_project.pull_node(d['full-line'], d['filename'], int(d['position']))
    return EMPTY

@app.route('/random-node', methods=['GET', 'POST'])
def random_node():
    d = request.form.to_dict()
    project_list.set_current_project(d['project'])
    node_id = project_list.current_project.random_node()
    project_list.nav_new(node_id)
    return json.dumps({
        'node_id' : node_id,
        'filename': project_list.current_project.nodes[node_id].filename,
        'position': project_list.current_project.nodes[node_id].ranges[0][0]
        })

@app.route('/completions', methods=['GET', 'POST'])
def completions():
    d = request.form.to_dict()
    project_list.set_current_project(d['project'])    
    return json.dumps({
        
        })

@app.route('/keywords', methods=['GET', 'POST'])
def keywords():
    d = request.form.to_dict()
    project_list.set_current_project(d['project'])
    r = { 'current_project' : project_list.current_project.title,
        'nodes' : {} }
    for n in project_list.current_project.nodes:
        r['nodes'][n] = {}
        if project_list.current_project.nodes[n].title.strip() == '':
            r['nodes'][n]['title'] = '(no title)'
        else:
            r['nodes'][n]['title'] = project_list.current_project.nodes[n].title
        r['nodes'][n]['date'] = str(project_list.current_project.nodes[n].date())
        r['nodes'][n]['position'] = project_list.current_project.nodes[n].ranges[0][0]
        r['nodes'][n]['id'] = project_list.current_project.nodes[n].id
        r['nodes'][n]['project_title'] = project_list.current_project.title        
        r['nodes'][n]['filename'] = os.path.join(project_list.current_project.path, project_list.current_project.nodes[n].filename)

    r['keyphrases'] = project_list.current_project.keywords
    return json.dumps(r)

@app.route('/associate', methods=['GET', 'POST'])
def associate():
    d = request.form.to_dict()
    project_list.set_current_project(d['project'])
    assoc_nodes = project_list.current_project.get_assoc_nodes(
        d['string'],
        d['filename'],
        int(d['position']))
    nodes = []
    for nid in assoc_nodes:
        if project_list.current_project.nodes[nid].title.strip() == '':
            title = '(no title)'
        else:
            title = project_list.current_project.nodes[nid].title
        next_node = {
            'id': nid,
            'filename' :os.path.join(project_list.current_project.path, project_list.current_project.nodes[nid].filename),            
            'position' :project_list.current_project.nodes[nid].ranges[0][0],
            'project_title' :project_list.current_project.title,
            'date' : str(project_list.current_project.nodes[nid].date()),
            'title' : title
        }
        nodes.append(next_node)
    return json.dumps({
        'nodes' : nodes,
        })

@app.route('/apply-patches', methods=['GET', 'POST'])
def apply_patches():
    d = request.form.to_dict()
    state = project_list.current_project.apply_patches(
        json.loads(d['history']), 
        distance_back=int(d['distance-back']))
    return json.dumps({ 'state' : state })

@app.route('/get-history', methods=['GET', 'POST'])
def get_history():
    d = request.form.to_dict()
    history = project_list.current_project.get_history(os.path.basename(d['filename']))
    return json.dumps({
        'history' : json.dumps(history),
        'timestamp-format': project_list.current_project.settings['timestamp_format']
        })

@app.route('/async-off', methods=['GET', 'POST'])
def async_off():
    for project in project_list.projects:
        print(project)
        project.is_async = False
    return EMPTY

@app.route('/log-node-meta', methods=['GET', 'POST'])
def log_node_meta():
    d = request.form.to_dict()
    print(d)
    node_id = project_list.current_project.get_node_id_from_position(d['filename'], int(d['position']))
    if not node_id:
        print('No Node found here')
        return EMPTY
    print(project_list.current_project.nodes[node_id].id)
    print(project_list.current_project.nodes[node_id].ranges)
    print(project_list.current_project.nodes[node_id].root_node)
    print(project_list.current_project.nodes[node_id].compact)
    print(project_list.current_project.nodes[node_id].export_points)
    project_list.current_project.nodes[node_id].metadata.log()
    return EMPTY




# NOT WORKING
@app.route('/search', methods=['GET', 'POST'])
def search():
    d = request.form.to_dict()
    search_results = project_list.current_project.search_term(d['string'])
    search_results.initiate_search()
    while not search_results.complete:
        time.sleep(1)
    return json.dumps({
            'results' : search_results.result
            })
    
app.run(host="127.0.0.1", use_reloader=False, port=5000, debug=True)
