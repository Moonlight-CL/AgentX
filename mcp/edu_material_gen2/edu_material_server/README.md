#local dev run cmd
cd /mcp/edu_material_gen2

uv sync
source .venv/bin/activate

cd /mcp/edu_material_gen2/edu_material_server
python -m edu_material_server --transport http --port 3666

#local docker run
docker run -p 3666:3666 --name edu-server edu_material_server

#for local docker network communication
docker network create shared-net
docker network connect shared-net edu-server
docker network connect shared-net postgres-demo-dev