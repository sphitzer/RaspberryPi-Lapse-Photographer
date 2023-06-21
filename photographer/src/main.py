
# Third-party library imports
import uvicorn
from fastapi import FastAPI, Query, BackgroundTasks
from loguru import logger
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from services.timelapse import Timelapse
from services.fileutils import FileUtils
from services.reprocess_timelapse import ReprocessTimelapse

app = FastAPI()

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    SimpleSpanProcessor(ConsoleSpanExporter())
)

FastAPIInstrumentor.instrument_app(app)

async def async_run_timelapse(output_path, name, interval, frames, kafka_bootstrap_servers):
    timelapse = Timelapse(output_path, name, interval, frames, kafka_bootstrap_servers)
    FileUtils.create_timelapse_dir(output_path, name)
    timelapse.run()

async def async_reprocess_timelapse(output_path, name, kafka_bootstrap_servers, topic_name):
    reprocess_timelapse = ReprocessTimelapse(output_path, name, kafka_bootstrap_servers, topic_name)
    reprocess_timelapse.reprocess()

@app.post("/start_timelapse/")
async def start_timelapse(
    background_tasks: BackgroundTasks,
    name: str = Query(..., description="Name of folder timelapse to be saved in"),
    output_path: str = Query(..., description="Output dir that will hold newly created timelapse dir", example="/output"),
    frames: int = Query(..., description="Total number of photos to be taken"),
    interval: int = Query(..., description="Time between each photo in seconds"),
    kafka_bootstrap_server: str = Query(..., description="Kafka bootstrap server, e.g. broker:9092", example="broker:9092"),
    ):
    background_tasks.add_task(async_run_timelapse, output_path, name, interval, frames, kafka_bootstrap_server)
    return {"message": "Timelapse started"}

@app.post("/reprocess_timelapse/")
async def reprocess_timelapse(
    background_tasks: BackgroundTasks,
    name: str = Query(..., description="Name of folder timelapse to be processed"),
    output_path: str = Query(..., description="Output dir where timelapse images are stored", example="/output"),
    kafka_bootstrap_servers: str = Query(..., description="Kafka bootstrap servers", example="broker:9092"),
    topic_name: str = Query(..., description="Name of kafka topic to place images on", example="timelapse_images4")
    ):
    background_tasks.add_task(async_reprocess_timelapse, output_path, name, kafka_bootstrap_servers, topic_name)
    return {"message": "Timelapse re-processing started"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8030)