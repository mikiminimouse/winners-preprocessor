#!/bin/bash

# Script to run the Downloader Microservice

cd /root/winners_preprocessor

case "$1" in
    "menu")
        echo "Starting Downloader Microservice - Interactive Menu"
        python3 services/downloader_microservice/menu.py
        ;;
    "cli")
        echo "Starting Downloader Microservice - CLI"
        shift
        python3 services/downloader_microservice/cli.py "$@"
        ;;
    "demo")
        echo "Running Downloader Microservice Demo"
        python3 services/downloader_microservice/demo.py
        ;;
    "test")
        echo "Running Downloader Microservice Tests"
        python3 services/downloader_microservice/test_downloader.py
        ;;
    *)
        echo "Downloader Microservice Runner"
        echo "Usage:"
        echo "  ./run_downloader.sh menu     - Interactive menu"
        echo "  ./run_downloader.sh cli      - Command line interface"
        echo "  ./run_downloader.sh demo     - Show demo"
        echo "  ./run_downloader.sh test     - Run tests"
        echo ""
        echo "Examples:"
        echo "  ./run_downloader.sh cli --limit 50"
        echo "  ./run_downloader.sh cli --health-check"
        ;;
esac
