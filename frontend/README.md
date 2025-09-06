# Run Frontend on Docker

1. Build the docker image
```shell
docker build -t sentiment-analysis:frontend .
```
2. Get the IP address of Backend container
```shell
BACKEND_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' backend)
```
3. Run the docker image
```shell
docker run -p 8501:8501 \
    --name frontend \
    -e BACKEND_API_URL="http://$BACKEND_IP:8000/predict" \
    sentiment-analysis:frontend
```
4. Access the UI at http://localhost:8501


# CleanUp
```shell
docker stop frontend
docker rm frontend
```