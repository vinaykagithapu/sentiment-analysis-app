# Run Backend on Docker

1. Build the docker image
```shell
docker build -t sentiment-analysis:backend .
```
2. Run the docker image
```shell
docker run -p 8000:8000 --name backend sentiment-analysis:backend
```
3. Wait for 5 mins it will download the model weights from huggingface
```shell
# List the models
curl -X GET http://localhost:8000/models

# Infer
curl -X POST "http://localhost:8000/predict" \
    -H "Content-Type: application/json" \
    -d '{
          "text": "I love this product!",
          "models": ["distilbert", "bertweet"]
     }'
```

# CleanUp
```shell
docker stop backend
docker rm backend
```