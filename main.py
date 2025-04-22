from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit  # Импортируем SocketIO
import json
import os
from threading import Lock

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'  # Секретный ключ для Flask-SocketIO
socketio = SocketIO(app)  # Инициализация SocketIO

# Construct the path to data.json and settings.json
base_dir = os.path.dirname(os.path.abspath(__file__))  # Current directory
data_path = os.path.join(base_dir, 'data.json')  # Path to data.json
settings_path = os.path.join(base_dir, 'settings.json')  # Path to settings.json

# Load data from JSON files
with open(data_path, 'r') as file:
    data = json.load(file)

with open(settings_path, 'r') as f:
    settings = json.load(f)

allow_decimal = settings["allow_decimal"]

# Shared state for the currently selected contestant
current_contestant = 1  # Default to the first contestant
lock = Lock()  # To ensure thread-safe updates

# Состояние экрана ожидания
waiting_screen_active = False

# WebSocket: Переключение экрана ожидания
@socketio.on('toggle_waiting_screen')
def handle_toggle_waiting_screen(data):
    global waiting_screen_active
    waiting_screen_active = data['active']
    # Отправляем состояние всем клиентам
    emit('update_waiting_screen', {'active': waiting_screen_active}, broadcast=True)
    
@app.route('/dashboard')
def dashboard():
    contestants = data['contestants']
    scores = data['scores']

    # Собираем средние оценки по каждому участнику
    averages = {}
    for score in scores:
        cnum = int(score['contestant'])
        averages.setdefault(cnum, []).append(score['weighted_score'])

    contestants_names = []
    contestants_averages = []

    for c in contestants:
        cnum = int(c['number'])
        name = c['name']
        if cnum in averages:
            avg = round(sum(averages[cnum]) / len(averages[cnum]), 2)
        else:
            avg = 0
        contestants_names.append(name)
        contestants_averages.append(avg)

    return render_template(
        'dashboard.html',
        contestants_names=contestants_names,
        contestants_averages=contestants_averages
    )


# Home route to select a judge
@app.route("/")
def select_judge():
    judges = data["judges"]
    return render_template("judge.html", judges=judges)

@app.route("/nav")
def nav():
    return render_template("nav.html")

# Route to select a category after choosing a judge
@app.route('/select_category')
def select_category():
    # Получаем имя судьи из URL параметра, либо берём первого из списка
    judge_name = request.args.get('judge', data['judges'][0])

    # Получаем все уникальные категории среди участников
    categories = sorted(set(c['category'] for c in data['contestants']))

    return render_template("select_category.html", judge=judge_name, categories=categories)

# Judging page for a selected category
@app.route("/judging", methods=["GET", "POST"])
def judging():
    judge = request.args.get("judge")
    category = request.args.get("category")
    contestants = [
        c for c in data["contestants"] if c["category"] == category
    ]
    criteria = data["criteria"]

    # Ensure previously judged contestants can't be judged again
    judged_contestants = {
        score["contestant"] for score in data["scores"] if score["judge"] == judge
    }

    if request.method == "POST":
        contestant = request.form.get("contestant")
        if not contestant:
            return "Contestant not selected", 400

        scores = []
        for criterion in criteria:
            criterion_name = criterion["name"]
            score = float(request.form.get(criterion_name, 0))

            # Validate score range
            if score < criterion["min_score"] or score > criterion["max_score"]:
                return f"Score for {criterion_name} must be between {criterion['min_score']} and {criterion['max_score']}", 400

            scores.append(score)

        # Calculate weighted score
        total_weight = sum(criterion["weight"] for criterion in criteria)
        weighted_score = sum(
            score * criterion["weight"] / total_weight for score, criterion in zip(scores, criteria)
        )

        # Save the score
        data["scores"].append({
            "judge": judge,
            "contestant": contestant,
            "weighted_score": round(weighted_score, 2),
        })
        save_data()

        return redirect(url_for("judging", judge=judge, category=category))

    return render_template(
        "judging.html",
        judge=judge,
        category=category,
        contestants=[c for c in contestants if c["number"] not in judged_contestants],
        criteria=criteria,
        allow_decimal=allow_decimal
    )

# Results page
@app.route("/results")
def results():
    contestants = {int(c["number"]): c for c in data["contestants"]}  # Преобразование ключей в int
    scores_by_contestant = {}

    for score_entry in data["scores"]:
        contestant_number = int(score_entry["contestant"])  # Убедимся, что ключ целочисленный
        weighted_score = score_entry["weighted_score"]
        scores_by_contestant.setdefault(contestant_number, []).append({
            "judge": score_entry["judge"],
            "weighted_score": weighted_score
        })

    # Calculate results by category
    results_by_category = {}
    for number, scores in scores_by_contestant.items():
        contestant = contestants[number]  # Используем int(number)
        category = contestant["category"]
        average_weighted_score = round(
            sum(s["weighted_score"] for s in scores) / len(scores), 2
        )

        results_by_category.setdefault(category, []).append({
            "number": number,
            "name": contestant["name"],
            "average_weighted_score": average_weighted_score,
            "scores": scores
        })

    # Sort results within each category
    for category, results in results_by_category.items():
        results.sort(key=lambda x: x["average_weighted_score"], reverse=True)

    return render_template("results.html", results_by_category=results_by_category, judges=data["judges"])
    
@app.route('/list')
def list():
    # Словарь оценок по номеру участника
    scored_contestants = {int(score["contestant"]) for score in data["scores"]}

    # Группируем участников по категориям
    participants_by_category = {}
    for contestant in sorted(data["contestants"], key=lambda c: (c["category"], c["number"])):
        category = contestant["category"]
        number = int(contestant["number"])  # Убедитесь, что номер — это целое число
        name = contestant["name"]
        has_scores = number in scored_contestants  # Проверка на наличие оценок

        participants_by_category.setdefault(category, []).append({
            "number": number,
            "name": name,
            "has_scores": has_scores
        })

    return render_template("list.html", participants_by_category=participants_by_category)


@app.route('/control')
def control_page():
    # Render the control page with a list of contestants
    return render_template('control.html', contestants=data['contestants'])

@app.route('/display')
def display_page():
    # Render the display page with the current contestant's scores
    return render_template('display.html')

@app.route('/get_current_contestant')
def get_current_contestant():
    # Return the currently selected contestant number
    with lock:
        return jsonify({"contestant_number": current_contestant})

@app.route('/set_current_contestant', methods=['POST'])
def set_current_contestant():
    # Update the currently selected contestant
    global current_contestant
    contestant_number = int(request.json.get('contestant_number'))
    with lock:
        current_contestant = contestant_number
    return jsonify({"status": "success", "contestant_number": current_contestant})

@app.route('/get_scores/<int:contestant_number>')
def get_scores(contestant_number):
    # Найти участника по номеру
    contestant = next((c for c in data['contestants'] if c['number'] == str(contestant_number)), None)
    
    # Если участник найден, то получить его оценки, иначе вернуть пустой список
    contestant_scores = [score for score in data['scores'] if int(score['contestant']) == contestant_number]
    
    return jsonify({
        "scores": contestant_scores,
        "contestant": contestant,
        "judges": data['judges']
    })


@app.route('/reset', methods=['POST'])
def reset_data():
    try:
        data['scores'] = []  # Очищаем только оценки
        save_data()
        return jsonify({'message': 'Data has been successfully reset.'})
    except Exception as e:
        return jsonify({'message': f'Error resetting data: {str(e)}'})


def save_data():
    with lock:
        with open(data_path, 'w') as f:
            json.dump(data, f, indent=4)


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0')  # Запуск с поддержкой WebSocket