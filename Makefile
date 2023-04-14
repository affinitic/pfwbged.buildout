#!/usr/bin/make

# requires BUILD_ID variable
build-docker-image:
	docker build -t docker-registry.pfwb.be/pfwb-ged:${BUILD_ID} .
	docker push docker-registry.pfwb.be/pfwb-ged:${BUILD_ID}

# requires BUILD_ID variable
deploy-docker-staging:
	docker stack deploy pfwb-ged-staging -c docker-compose-staging.yml

# requires BUILD_ID variable
deploy-docker-prod:
	docker stack deploy pfwb-ged-prod -c docker-compose-prod.yml

remove_duplicate_contacts:
	PYTHONIOENCODING=utf-8 ./bin/instance1 run ./scripts/remove_duplicate_contacts.py pfwbged

