# ComfyUI-ShellAgent-Plugin

This repository provides utility nodes for defining inputs and outputs in ComfyUI workflows. These nodes are essential for running [ShellAgent](https://github.com/myshell-ai/ShellAgent) apps with ComfyUI, but they can also be used independently to specify input/output variables and their requirements explicitly.

## Installation

To install, either:

1. Download or clone this repository into the ComfyUI/custom_nodes/ directory.
2. Use the ComfyUI-Manager.

## Features

### Input Nodes

- Input Text
- Input Image
- Input Float
- Input Integer

Each input node supports setting a default value and additional configuration options.

### Output Nodes

- Save Image
- Save Images
- Save Video - VHS

### Convert Widgets to ShellAgent Inputs

A widget can be easily converted into a ShellAgent Input node of the appropriate type by right-clicking on the widget and selecting the option from the menu.
