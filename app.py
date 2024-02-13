from flask import Flask, request, jsonify, render_template
import json
import os
import time

app = Flask(__name__)

# Class to represent each place node in the BST
class PlaceNode:
    def __init__(self, user_id, place_name, country, region, vote_count=1):
        self.user_id = user_id
        self.place_name = place_name
        self.country = country
        self.region = region
        self.vote_count = vote_count
        self.voted_users = set()  # Using a set to store voted users for faster membership checking
        self.voted_users.add(user_id)
        self.comments = []  # List to store comments for each vote
        self.left = None
        self.right = None

# BST class to manage the places
class BST:
    def __init__(self):
        self.root = None

    def insert(self, root, node):
        if root is None:
            return node
        else:
            if node.place_name < root.place_name:
                root.left = self.insert(root.left, node)
            elif node.place_name > root.place_name:
                root.right = self.insert(root.right, node)
        return root

    def search(self, root, place_name):
        # Base cases: root is null or place_name is present at root
        if root is None or root.place_name == place_name:
            return root

        # Place_name is greater than root's place_name
        if root.place_name < place_name:
            return self.search(root.right, place_name)
        
        # Place_name is smaller than root's place_name
        return self.search(root.left, place_name)

    def vote(self, place_name, user_id, comment):
        node = self.search(self.root, place_name)
        if node:
            # Check if the user has already voted for this place
            if user_id in node.voted_users:
                return False  # User has already voted, return False
            else:
                node.vote_count += 1
                node.comments.append(comment)
                node.voted_users.add(user_id)  # Add the user ID to voted_users set
                return True  # Vote recorded successfully
        else:
            return False  # Place not found, return False

    def inorder_traversal(self, root, filter_func=None):
        res = []
        if root:
            res = self.inorder_traversal(root.left, filter_func)
            if not filter_func or filter_func(root):
                res.append({'place_name': root.place_name, 'country': root.country, 'region': root.region, 'vote_count': root.vote_count,'comments':root.comments})
            res = res + self.inorder_traversal(root.right, filter_func)
        return res
    
    # Function to recursively search for a user ID within the BST
    def user_id_exists(self, root, user_id):
        if root is None:
            return False
        if user_id in root.voted_users or root.user_id == user_id:
            return True
        return self.user_id_exists(root.left, user_id) or self.user_id_exists(root.right, user_id)

    def compare_user_id_view_voted(self, node):
        return self.user_id in node.voted_users
    
    def compare_user_id_not_voted(self, node):
        return self.user_id not in node.voted_users

# Global BST instance to store places
places_bst = BST()

# File paths
MAIN_FILE_PATH = 'main.txt'
LOG_FILE_PATH = 'log.txt'


def load_main_file_data():
    if os.path.exists(MAIN_FILE_PATH):
        with open(MAIN_FILE_PATH, 'r') as main_file:
            data = main_file.readlines()
            for line in data:
                entry = json.loads(line)
                if entry['type'] == 'proposal':
                    new_node = PlaceNode(entry['user_id'], entry['place_name'], entry['country'], entry['region'])
                    places_bst.root = places_bst.insert(places_bst.root, new_node)
                elif entry['type'] == 'vote':                
                    place_name = entry['place_name']
                    user_id = entry['user_id']
                    comment = entry.get('comment', '')  # 如果有评论字段，则获取评论，否则设置为空字符串
                    node = places_bst.search(places_bst.root, place_name)
                    if node:
                        if user_id in node.voted_users:
                            # 如果用户已经投过票，则返回错误消息
                            print(f"User {user_id} has already voted for place {place_name}")
                        else:
                            # 增加投票计数和记录投票者的信息
                            node.vote_count += 1
                            node.voted_users.add(user_id)
                            node.comments.append(comment)
                            #print(f"Vote recorded for place {place_name} by user {user_id}")
                    else:
                        # 如果找不到该地点，则返回错误消息
                        print(f"Place {place_name} not found")


# 更新定时任务以将数据从日志文件转移到主文件并清空日志文件
def transfer_data_from_log_to_main():
    if os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, 'r') as log_file:
            log_data = log_file.readlines()
        with open(MAIN_FILE_PATH, 'a') as main_file:
            for line in log_data:
                main_file.write(line)
        # 清空日志文件
        open(LOG_FILE_PATH, 'w').close()


# Append data to log file
def append_to_log_file(data):
    with open(LOG_FILE_PATH, 'a') as log_file:
        log_file.write(json.dumps(data) + '\n')

def check_and_transfer_data():
    if os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, 'r') as log_file:
            log_data = log_file.readlines()
        if log_data:
            with open(MAIN_FILE_PATH, 'a') as main_file:
                for line in log_data:
                    main_file.write(line)
            # 清空日志文件
            open(LOG_FILE_PATH, 'w').close()



check_and_transfer_data()

# Load main file data into BST on startup
load_main_file_data()
# 在启动服务器时调用 check_and_transfer_data() 函数


# Set up a periodic task to transfer data from log file to main file and clear log file
def periodic_task():
    while True:
        time.sleep(900)  # Sleep for 15 minutes
        transfer_data_from_log_to_main()

# Start periodic task in a separate thread
import threading
threading.Thread(target=periodic_task).start()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin_page.html')

@app.route('/graphData')
def plot_graph():
    places = places_bst.inorder_traversal(places_bst.root)
    #print(places)
    return jsonify(sorted(places, key=lambda place: place["vote_count"])[:-6:-1]), 200

@app.route('/propose', methods=['POST'])
def propose_place():
    data = request.json
    user_id, place_name, country, region = data['user_id'], data['place_name'], data['country'], data['region']
    if not (user_id and place_name and country and region):
        return jsonify ({'message': 'All details were not entered. Try again'}), 400
    else:
        if places_bst.search(places_bst.root, place_name) is None:
            data['type'] = 'proposal'  # add type as 'proposal'
            
            new_node = PlaceNode(user_id, place_name, country, region)
            places_bst.root = places_bst.insert(places_bst.root, new_node)
            append_to_log_file(data)  # Append to log file
            return jsonify({'message': 'Place proposed successfully'}), 201
        else:
            return jsonify({'message': 'Place already proposed'}), 400

@app.route('/vote', methods=['POST'])
def vote_for_place():
    data = request.json
    place_name, user_id, comment = data['place_name'], data['user_id'], data['comment']
    node = places_bst.search(places_bst.root, place_name)
    if node:
        if user_id in node.voted_users:
            return jsonify({'message': 'You have already voted for this place'}), 400
        else:
            data['type'] = 'vote'  # add 'type' as 'vote'
            
            if places_bst.vote(place_name, user_id, comment):
                append_to_log_file(data)  # Append to log file
                return jsonify({'message': 'Vote recorded successfully'}), 200
            else:
                return jsonify({'message': 'Failed to record vote'}), 400
    else:
        return jsonify({'message': 'Place not found'}), 404

@app.route('/view-voted', methods=['GET'])
def view_voted_places():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'message': 'User ID is required'}), 400
    if not places_bst.user_id_exists(places_bst.root, user_id):
        return jsonify({'message': 'User not found'}), 404
    else:
        def filter_user_voted(node):
            return user_id in node.voted_users
        places = places_bst.inorder_traversal(places_bst.root, filter_user_voted)
        return jsonify(places), 200

@app.route('/view-except-voted', methods=['GET'])
def view_except_voted_places():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'message': 'User ID is required'}), 400
    places_bst.user_id = user_id
    places = places_bst.inorder_traversal(places_bst.root, places_bst.compare_user_id_not_voted)
    return jsonify(places), 200

@app.route('/filter', methods=['GET'])
def filter_places():
    country = request.args.get('country',None)
    region = request.args.get('region', None)

    def filter_func(node):
        conditions = []
        if country:
            conditions.append(node.country == country)
        if region:
            conditions.append(node.region == region)
        return all(conditions)

    places = places_bst.inorder_traversal(places_bst.root, filter_func)
    return jsonify(places), 200


if __name__ == '__main__':
    app.run(debug=False, port=5000)



