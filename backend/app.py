from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import select, create_engine, ForeignKey, types, Integer, Column, String, MetaData, Date, DateTime
from sqlalchemy.ext.asyncio import create_async_engine,  AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
import asyncio, uuid, aiofiles
from datetime import datetime, date

"""
First of all, I create an async table calles 'task_list_table'  where I save all 
data. (not order)
"""
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

DATABASE_URL = "sqlite+aiosqlite:///databases/database.db"
engine = create_async_engine(DATABASE_URL, echo=True)

# Async session maker for the engine
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


class Task_list_table(Base):
    __tablename__ = "Task_list_table"

    ID = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    Title = Column(String(55), nullable=False)
    Text = Column(String(3000), nullable=False)
    DeadLine = Column(DateTime, nullable=False)
    Start_Day = Column(Date)

    def __repr__(self):
        return f"{self.Title}"

async def write_task_to_file_txt(task):
    async with aiofiles.open("task.txt", "w") as f:
        await f.write(f"{task['title']}, {task['text']}, {task['deadline']}, {task['start_day']}")




@app.route('/')
def main():
    return "<h1>Server is runing!</h1>"

@app.route('/get_task_and_ddbb', methods=['POST'])
async def insert_database():
    """Insert a task into the database."""
    data = request.json

    start_date_provided = False

    # Parsing start_day
    if 'start_day' in data and data['start_day']:
        start_date_provided = True
        start_year, start_month, start_day_num = map(int, data['start_day'].split('-'))

    # Parsing DeadLine
    date_part, time_part = data['deadline'].split('T')
    year, month, day = map(int, date_part.split('-'))
    hour, minute = map(int, time_part.split(':'))

    new_task = Task_list_table(
        Title=data['title'],
        Text=data['text'],
        DeadLine=datetime(year, month, day, hour=hour, minute=minute),
        Start_Day=date(start_year, start_month, start_day_num) if start_date_provided else None
    )

    async with AsyncSessionLocal() as session:
        session.add(new_task)
        try:
            await session.commit()  # Try to commit
            return jsonify({"Result": f"Task called '{data['title']}' registered successfully!"})

        except Exception as e:
            print(str(e))
            return jsonify({"Error":{"Message":"(POST /get_task_and_ddbb)","Type":"ConnectionError","Param":None}})


@app.route('/get_all_taks')
@app.route('/get_all_taks/<string:apiKey>')
async def get_data(apiKey = None):
    """Get all posts from the database and send to frontend"""
    if apiKey == "12345" or apiKey == "abcde":
        async with AsyncSessionLocal() as session:
            try:
                # Use select from SQLAlchemy to feth all tasks
                stmt = select(Task_list_table)
                result = await session.execute(stmt)
                tasks = result.scalars().all()

                # Convert ORM objects o dictionaries for JSON response
                tasks_list = [{
                    "ID": task.ID,
                    "Title": task.Title,
                    "Text": task.Text,
                    "DeadLine": [part if c == 0 else part[:-3] for c, part in enumerate(task.DeadLine.isoformat().split('T'))] if task.DeadLine else None,
                    "Start_Day": task.Start_Day.isoformat() if task.Start_Day else None 
                } for task in tasks]

                return jsonify({"Response": tasks_list})
            
            except Exception as e:
                print(e)
                return jsonify({"Error":e})
            
    return jsonify({"Error":"Error url, you don't provided the API key (GET /get_all_taks/<string:apiKey> )"})


@app.route('/remove_single_task')
@app.route('/remove_single_task/<string:apiKey>')
@app.route('/remove_single_task/<string:apiKey>/<string:task_id>')
async def remove_task(task_id = None, apiKey = None):
    """Delete a task from the database with its ID. Apikey is required"""
    if apiKey == "12345" or apiKey == "abcde":
        async with AsyncSessionLocal() as sess:
            try:
                select_task = await sess.execute(select(Task_list_table).filter_by(ID=task_id))
                task_instance = select_task.scalar_one_or_none()       
                if not task_instance: # In case task not found
                    return jsonify({"Response": {"Message": f"No task found with ID {task_id}", "Status":"Error"}})
                await sess.delete(task_instance)
                await sess.commit()

                return jsonify({"Response": {"Message": f" Task {task_id} removed!", "Status": "Success"}})
            
            except Exception as e:
                print(e)
                return jsonify({"Error":e})                

    return jsonify({"Error": "Invalid URL (GET /remove_single_task/<apiKey>/<task_id>)"})


@app.route('/edit_single_task')
@app.route('/edit_single_task/<string:apiKey>')
@app.route('/edit_single_task/<string:apiKey>/<string:task_id>', methods=['POST','GET'])
async def edit_task(apiKey = None, task_id=None):
    """
    Endpoint to edit a single task based on its ID.
    """
    if apiKey not in ['12345','abcde']:
        return jsonify({"Error": "Invalid URL (POST GET /remove_single_task/<apiKey>/<task_id>)"})

    data = request.json
    async with AsyncSessionLocal() as sess:
        
        # Select task based on ID
        stmt = sess.execute(select(Task_list_table).filter_by(ID=task_id).limit(1)) # Select table 
        task_instance = stmt.scalar_one_or_none()  

        if task_instance: # In case task not found
            return jsonify({"Response": f"Task {task_id} not found!", "Status": "Error"})
        
        # Update task fields
        if data.get('NewLine'):
            task_instance.Line = data['NewLine']
        if data.get('NewText'):
            task_instance.Text = data['NewText']
        if data.get('NewDeadline'):
            task_instance.Deadline = data['NewDeadline']
        if data.get('NewStartDay'):
            task_instance.StartDay = data['NewStartDay']

        # Commit chages
        await sess.commit()


    return jsonify({"Message":"This module is actually making"})   



@app.route("/return_something")
@app.route("/return_something/<string:arg>")
def return_something(arg = None):
    result = list(arg.split('_'))

    MyResult = {"Result": {
        "message": "Your mum is a thong! -> " + str(" ".join(result)),
        "type": "invalid_request_error",
        "param": None,
        "code": None}
    }

    return jsonify(MyResult)


@app.errorhandler(404)
def page_not_found(e):
    error_mesage = {
    "error": {
        "message": "Invalid URL (GET /remove_single_task | /get_all_taks | /edit_single_task | POST /get_task_and_ddbb )",
        "type": "invalid_request_error",
        "param": None,
        "code": None
    }
}
    return jsonify(error_mesage)

async def init_db():
    """Init the database with this async function"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == '__main__':
    asyncio.run(init_db())
    app.run(debug=True)


