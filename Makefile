REPOSITORY := chatwork

.PHONY: build
build:
	docker build -t $(REPOSITORY)/kube-schedule-scaler .;
	@version=$$(git rev-parse --short HEAD); \
		if [ -n "$$version" ]; then \
			docker tag $(REPOSITORY)/kube-schedule-scaler:latest $(REPOSITORY)/kube-schedule-scaler:$$version; \
		fi

.PHONY: push
push:
	@version=$$(git rev-parse --short HEAD); \
		if [ -n "$$version" ]; then \
			docker tag $(REPOSITORY)/kube-schedule-scaler:latest $(REPOSITORY)/kube-schedule-scaler:$$version; \
		fi
	docker buildx build --platform linux/amd64,linux/arm64 -t $(REPOSITORY)/kube-schedule-scaler:$$version --push .;
