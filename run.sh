#!/bin/bash

SCRIPT_PATH="$0"
ROOT_DIR=$(dirname $SCRIPT_PATH)
cd $ROOT_DIR # change to the script directory

IMAGE_NAME=renovate-catalog
IMAGE_TAG=latest

COMMON_DOCKER_ARGS="--rm -v $ROOT_DIR/:/repo -u $(id -u):$(id -g)"

function build_site(){
    echo "Building site..."
    docker run $COMMON_DOCKER_ARGS -i -w /repo \
        -e AZURE_CANONICAL_PASSWORD="$AZURE_CANONICAL_PASSWORD" \
        -e AZURE_CANONICAL_USER="$AZURE_CANONICAL_USER" \
        $IMAGE_NAME:$IMAGE_TAG bash << EOF
        
        src/get_reg_info.py -r canonical.azurecr.io \
        -u $AZURE_CANONICAL_USER \
        -p $AZURE_CANONICAL_PASSWORD \
        -o site

        src/gen_images_yaml.py \
            -t site/canonical.azurecr.io/index.tsv \
            -o site/canonical.azurecr.io/images.yaml

        # This could be replaced with something better, but it works for now
        tree site -T "Renovate Catalog" -H . -o site/index.html
        
EOF
}

function help_msg(){
    echo "Usage: $0 <action>"
}

function build_dev_image(){
    # TODO: add a flag to force rebuild
    echo "Building development image..."
    if  ! docker inspect $IMAGE_NAME:$IMAGE_TAG &> /dev/null \
        || [ "$1" == "force" ]; then
        docker build -t $IMAGE_NAME:$IMAGE_TAG .
    else
        echo "Development image already exists."
    fi
}

function save_dev_image(){
    echo "Saving the development image..."
    if [ -z "$1" ]; then
        echo "expected image archive as argument."
        exit 1
    fi
    docker save $IMAGE_NAME:$IMAGE_TAG > "$1"
}

function load_dev_image(){
    echo "Loading the development image..."
    if [ -z "$1" ]; then
        echo "expected image archive as argument."
        exit 1
    fi
    docker load < "$1"
}

function image_shell(){
    echo "Entering development image shell..."
    docker run $COMMON_DOCKER_ARGS -it -w /repo \
        $IMAGE_NAME:$IMAGE_TAG /bin/bash
}

function setup_worktree(){
    echo "Setting up worktree..."
    git fetch --all
    git worktree add "$ROOT_DIR/site" site
}

function push_changes() {
    local dir="$1"
    local commit_msg="$2"

    if [ -z "$commit_msg" ]; then
        echo "Commit message is required."
        exit 1
    fi

    pushd "$dir"
        if git diff-index --quiet HEAD; then
            echo "No changes to commit"
            exit
        fi
        git add -A
        git -c user.name='Dashboard Worker' -c user.email='' \
            commit -m "$commit_msg"
        git push
    popd
}

if [ -z "$1" ]; then
    help_msg
    exit 1
fi

action="$1"
shift # capture remaining arguments
args="$@" 
case "$action" in

    build_site)
        build_site $args
        ;;

    # development image management
    load_image)
        load_dev_image $args
        ;;
    build_image)
        build_dev_image force $args
        ;;
    save_image)
        build_dev_image $args
        save_dev_image $args
        ;;
    setup)
        build_dev_image $args
        setup_worktree $args
        ;;
    image_shell)
        image_shell $args
        ;;
    push_site)
        push_changes site "$args"
    ;;

    *)
        help_msg $args
        exit 1
        ;;
esac
