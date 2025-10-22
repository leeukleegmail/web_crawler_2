CONTAINER_NAME="web_crawler_2"
CONTAINER_PORT="5009"

docker stop $CONTAINER_NAME
docker rm $CONTAINER_NAME
docker build --tag $CONTAINER_NAME --build-arg container_name=$CONTAINER_NAME .
docker run -d -p 5001:$CONTAINER_PORT --name $CONTAINER_NAME --restart unless-stopped -v $(pwd)/:/$CONTAINER_NAME $CONTAINER_NAME

