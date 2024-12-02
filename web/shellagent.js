import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
  name: "Shellagent.extension",
  async setup() {
    window.parent.postMessage({
      type: 'loaded'
    }, '*');
    window.addEventListener('message', (event) => {
      if (event.data.type === 'save') {
        app.graphToPrompt().then(data => {
          window.parent.postMessage({
            prompt: data?.output || {},
            workflow: data?.workflow || {},
            type: 'save'
          }, "*");
        });
      }
      if (event.data.type === 'load') {
        app.loadGraphData(event.data.data, true, false);
      }
      if (event.data.type === 'load_default') {
        // 使用FileReader读取JSON文件
        fetch('extensions/ComfyUI-ShellAgent-Plugin/shellagent_default.json')
          .then(response => response.blob())
          .then(blob => {
            const reader = new FileReader();
            reader.onload = function (e) {
              const json = JSON.parse(e.target.result);
              app.loadGraphData(json, true, false);
            };
            reader.readAsText(blob);
          })
          .catch(error => console.error('加载默认JSON文件时出错:', error));
      }
    });
  },
  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (["ShellAgentPluginOutputText", "ShellAgentPluginOutputFloat", "ShellAgentPluginOutputInteger"].indexOf(nodeData.name) > -1) {
      chainCallback(nodeType.prototype, "onNodeCreated", function () {
        this.convertWidgetToInput(this.widgets[0])
      })
    }

    if (["ShellAgentPluginInputText", "ShellAgentPluginInputFloat", "ShellAgentPluginInputInteger"].indexOf(nodeData.name) > -1) {
      chainCallback(nodeType.prototype, "onNodeCreated", function () {
        const widget = this.widgets.find(w => w.name === 'choices')
        this.addWidget('button', 'manage choices', null, () => {
          const container = document.createElement("div");
          Object.assign(container.style, {
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "10px",
          });

          const addNew = document.createElement("button");
          addNew.textContent = "Add New";
          addNew.classList.add("pysssss-presettext-addnew");
          Object.assign(addNew.style, {
            fontSize: "13px",
            gridColumn: "1 / 3",
            color: "dodgerblue",
            width: "auto",
            textAlign: "center",
          });
          addNew.onclick = () => {
            addRow("");
          };
          container.append(addNew);

          function addRow(p) {

            const value = document.createElement("input");
            if (["ShellAgentPluginInputFloat", "ShellAgentPluginInputInteger"].indexOf(nodeData.name) > -1) {
              value.type = 'number';
            }

            const valueLbl = document.createElement("label");
            value.value = p;
            Object.assign(value.style, {
              width: "250px",
            });
            valueLbl.textContent = "Value:";
            valueLbl.append(value);

            Object.assign(valueLbl.style, {
              gridColumn: "1 / 3",
              width: "auto",
            });

            addNew.before(valueLbl);
          }

          let arr = []
          if (typeof widget.value === 'string') {
            try {
              arr = JSON.parse(widget.value)
            } catch { }
          } else if (Array.isArray(widget.value)) {
            arr = widget.value
          }

          for (const a of arr) {
            addRow(a);
          }

          const help = document.createElement("span");
          help.textContent = "To remove a item set the value to blank";
          help.style.gridColumn = "1 / 3";
          container.append(help);

          dialog.show("");
          dialog.textElement.append(container);
        })

        const dialog = new app.ui.dialog.constructor();
        dialog.element.classList.add("comfy-settings");

        const closeButton = dialog.element.querySelector("button");
        closeButton.textContent = "CANCEL";
        const saveButton = document.createElement("button");
        saveButton.textContent = "SAVE";
        saveButton.onclick = function () {
          const inputs = dialog.element.querySelectorAll("input");
          const p = [];
          for (let i = 0; i < inputs.length; i += 1) {
            const v = inputs[i];
            if (!v.value.trim()) {
              continue;
            }
            p.push(v.value);
          }

          widget.value = p;

          dialog.close();
        };

        closeButton.before(saveButton);
      })
    }

    if (['LoadImage', 'LoadImageMask'].indexOf(nodeData.name) > -1) {
      addMenuHandler(nodeType, function (_, options) {
        options.unshift({
          content: "Replace with ShellAgent Input Image",
          callback: () => {
            const node = addNode("ShellAgentPluginInputImage", this, { before: true });

            const dvn = node.widgets.find(w => w.name === 'default_value')
            dvn.value = this.widgets.find(w => w.name === 'image')?.value

            app.graph.links.filter(l => l != null)
              .forEach(l => {
                const tn = app.graph._nodes_by_id[l.target_id]
                node.connect(0, tn, 0)
              })
            app.graph.remove(this);
          }
        })
      })
    }

    if (nodeData.name === "ShellAgentPluginInputImage") {
      if (
        nodeData?.input?.required?.default_value?.[1]?.image_upload === true
      ) {
        nodeData.input.required.upload = [
          "IMAGEUPLOAD",
          { widget: "default_value" },
        ];
      }
    }

    if (nodeData.name === "ShellAgentPluginInputVideo") {
      addUploadWidget(nodeType, nodeData, "default_value");
      chainCallback(nodeType.prototype, "onNodeCreated", function () {
        const pathWidget = this.widgets.find((w) => w.name === "default_value");
        chainCallback(pathWidget, "callback", (value) => {
          if (!value) {
            return;
          }
          let parts = ["input", value];
          let extension_index = parts[1].lastIndexOf(".");
          let extension = parts[1].slice(extension_index + 1);
          let format = "video"
          if (["gif", "webp", "avif"].includes(extension)) {
            format = "image"
          }
          format += "/" + extension;
          let params = { filename: parts[1], type: parts[0], format: format };
          this.updateParameters(params, true);
        });
      });
      addLoadVideoCommon(nodeType, nodeData);
    }

    if (nodeData.name.indexOf('ShellAgentPlugin') === -1) {
      addMenuHandler(nodeType, function (_, options) {

        if (this.widgets) {
          let toInput = [];
          for (const w of this.widgets) {
            if (["customtext"].indexOf(w.type) > -1) {
              toInput.push({
                content: w.name,
                submenu: {
                  options: [
                    {
                      content: 'Input Text',
                      callback: () => {
                        this.convertWidgetToInput(w);
                        const node = addNode("ShellAgentPluginInputText", this, { before: true });
                        const dvn = node.widgets.find(w => w.name === 'default_value')
                        dvn.value = w.value;
                        node.connect(0, this, this.inputs.length - 1);
                      }
                    }
                  ]
                },
              })
            }
            if (["number"].indexOf(w.type) > -1) {
              toInput.push({
                content: w.name,
                submenu: {
                  options: [
                    {
                      content: 'Input Interger',
                      callback: () => {
                        this.convertWidgetToInput(w);
                        const node = addNode("ShellAgentPluginInputInteger", this, { before: true });
                        const dvn = node.widgets.find(w => w.name === 'default_value')
                        dvn.value = w.value;
                        node.connect(0, this, this.inputs.length - 1);
                      }
                    },
                    {
                      content: 'Input Float',
                      callback: () => {
                        this.convertWidgetToInput(w);
                        const node = addNode("ShellAgentPluginInputFloat", this, { before: true });
                        const dvn = node.widgets.find(w => w.name === 'default_value')
                        dvn.value = w.value;
                        node.connect(0, this, this.inputs.length - 1);
                      }
                    }
                  ]
                }
              })
            }
          }
          if (toInput.length) {
            options.unshift({
              content: "Convert to ShellAgent (Input)",
              submenu: {
                options: toInput
              }
            })
          }
        }

        if (this.outputs) {
          let toOutput = [];
          for (const o of this.outputs) {
            if (o.type === 'IMAGE') {
              toOutput.push({
                content: o.name,
                submenu: {
                  options: [
                    {
                      content: 'Save Image',
                      callback: () => {
                        const node = addNode("ShellAgentPluginSaveImage", this);
                        this.connect(0, node, 0);
                      }
                    },
                    {
                      content: 'Save Images',
                      callback: () => {
                        const node = addNode("ShellAgentPluginSaveImages", this);
                        this.connect(0, node, 0);
                      }
                    }
                  ]
                }

              })
            }

            if (o.type === 'STRING') {
              toOutput.push({
                content: o.name,
                submenu: {
                  options: [
                    {
                      content: `Output Text`,
                      callback: () => {
                        const node = addNode("ShellAgentPluginOutputText", this);
                        this.connect(0, node, 0);
                      }
                    },
                    {
                      content: `Output Float`,
                      callback: () => {
                        const node = addNode("ShellAgentPluginOutputFloat", this);
                        this.connect(0, node, 0);
                      }
                    },
                    {
                      content: `Output Integer`,
                      callback: () => {
                        const node = addNode("ShellAgentPluginOutputInteger", this);
                        this.connect(0, node, 0);
                      }
                    }
                  ]
                }
              })
            }

            if (o.type === "VHS_FILENAMES") {
              toOutput.push({
                content: o.name,
                submenu: {
                  options: [
                    {
                      content: `Save Video - VHS`,
                      callback: () => {
                        const node = addNode("ShellAgentPluginSaveVideoVHS", this);
                        this.connect(0, node, 0);
                      }
                    }
                  ]
                }
              })
            }
          }

          if (toOutput.length) {
            options.unshift({
              content: "Connect to ShellAgent (Output)",
              submenu: {
                options: toOutput
              }
            })
          }

        }
      })
    }
  },

  afterConfigureGraph(missingNodeTypes, app) {
    function addIn(type, nodeId) {
      if (LiteGraph.slot_types_default_in[type].indexOf(nodeId) === -1) {
        LiteGraph.slot_types_default_in[type].unshift(nodeId)
      }
    }

    function addOut(type, nodeId) {
      if (LiteGraph.slot_types_default_out[type].indexOf(nodeId) === -1) {
        LiteGraph.slot_types_default_out[type].unshift(nodeId)
      }
    }

    addIn('IMAGE', 'ShellAgentPluginInputImage')
    addOut('IMAGE', 'ShellAgentPluginSaveImage')
    addOut('IMAGE', 'ShellAgentPluginSaveImages')
    // addOut('STRING', 'ShellAgentPluginOutputInteger')
    // addOut('STRING', 'ShellAgentPluginOutputFloat')
    // addOut('STRING', 'ShellAgentPluginOutputText')
  }
});

function addMenuHandler(nodeType, cb) {
  const getOpts = nodeType.prototype.getExtraMenuOptions;
  nodeType.prototype.getExtraMenuOptions = function () {
    const r = getOpts.apply(this, arguments);
    cb.apply(this, arguments);
    return r;
  };
}

function fitHeight(node) {
  node.setSize([node.size[0], node.computeSize([node.size[0], node.size[1]])[1]])
  node?.graph?.setDirtyCanvas(true);
}

function addNode(name, nextTo, options) {
  options = { select: true, shiftY: 0, before: false, ...(options || {}) };
  const node = LiteGraph.createNode(name);
  app.graph.add(node);
  node.pos = [
    options.before ? nextTo.pos[0] - node.size[0] - 30 : nextTo.pos[0] + nextTo.size[0] + 30,
    nextTo.pos[1] + options.shiftY,
  ];
  if (options.select) {
    app.canvas.selectNode(node, false);
  }
  return node;
}

function chainCallback(object, property, callback) {
  if (object == undefined) {
    //This should not happen.
    console.error("Tried to add callback to non-existant object")
    return;
  }
  if (property in object && object[property]) {
    const callback_orig = object[property]
    object[property] = function () {
      const r = callback_orig.apply(this, arguments);
      callback.apply(this, arguments);
      return r
    };
  } else {
    object[property] = callback;
  }
}

async function uploadFile(file) {
  //TODO: Add uploaded file to cache with Cache.put()?
  try {
    // Wrap file in formdata so it includes filename
    const body = new FormData();
    const i = file.webkitRelativePath.lastIndexOf('/');
    const subfolder = file.webkitRelativePath.slice(0, i + 1)
    const new_file = new File([file], file.name, {
      type: file.type,
      lastModified: file.lastModified,
    });
    body.append("image", new_file);
    if (i > 0) {
      body.append("subfolder", subfolder);
    }
    const resp = await api.fetchApi("/upload/image", {
      method: "POST",
      body,
    });

    if (resp.status === 200) {
      return resp
    } else {
      alert(resp.status + " - " + resp.statusText);
    }
  } catch (error) {
    alert(error);
  }
}

function addVideoPreview(nodeType) {
  chainCallback(nodeType.prototype, "onNodeCreated", function () {
    var element = document.createElement("div");
    const previewNode = this;
    var previewWidget = this.addDOMWidget("videopreview", "preview", element, {
      serialize: false,
      hideOnZoom: false,
      getValue() {
        return element.value;
      },
      setValue(v) {
        element.value = v;
      },
    });
    previewWidget.computeSize = function (width) {
      if (this.aspectRatio && !this.parentEl.hidden) {
        let height = (previewNode.size[0] - 20) / this.aspectRatio + 10;
        if (!(height > 0)) {
          height = 0;
        }
        this.computedHeight = height + 10;
        return [width, height];
      }
      return [width, -4];//no loaded src, widget should not display
    }
    element.addEventListener('contextmenu', (e) => {
      e.preventDefault()
      return app.canvas._mousedown_callback(e)
    }, true);
    element.addEventListener('pointerdown', (e) => {
      e.preventDefault()
      return app.canvas._mousedown_callback(e)
    }, true);
    element.addEventListener('mousewheel', (e) => {
      e.preventDefault()
      return app.canvas._mousewheel_callback(e)
    }, true);
    previewWidget.value = {
      hidden: false, paused: false, params: {},
      muted: app.ui.settings.getSettingValue("VHS.DefaultMute", false)
    }
    previewWidget.parentEl = document.createElement("div");
    previewWidget.parentEl.className = "vhs_preview";
    previewWidget.parentEl.style['width'] = "100%"
    element.appendChild(previewWidget.parentEl);
    previewWidget.videoEl = document.createElement("video");
    previewWidget.videoEl.controls = false;
    previewWidget.videoEl.loop = true;
    previewWidget.videoEl.muted = true;
    previewWidget.videoEl.style['width'] = "100%"
    previewWidget.videoEl.addEventListener("loadedmetadata", () => {

      previewWidget.aspectRatio = previewWidget.videoEl.videoWidth / previewWidget.videoEl.videoHeight;
      fitHeight(this);
    });
    previewWidget.videoEl.addEventListener("error", () => {
      //TODO: consider a way to properly notify the user why a preview isn't shown.
      previewWidget.parentEl.hidden = true;
      fitHeight(this);
    });
    previewWidget.videoEl.onmouseenter = () => {
      previewWidget.videoEl.muted = previewWidget.value.muted
    };
    previewWidget.videoEl.onmouseleave = () => {
      previewWidget.videoEl.muted = true;
    };

    previewWidget.imgEl = document.createElement("img");
    previewWidget.imgEl.style['width'] = "100%"
    previewWidget.imgEl.hidden = true;
    previewWidget.imgEl.onload = () => {
      previewWidget.aspectRatio = previewWidget.imgEl.naturalWidth / previewWidget.imgEl.naturalHeight;
      fitHeight(this);
    };

    var timeout = null;
    this.updateParameters = (params, force_update) => {
      if (!previewWidget.value.params) {
        if (typeof (previewWidget.value != 'object')) {
          previewWidget.value = { hidden: false, paused: false }
        }
        previewWidget.value.params = {}
      }
      Object.assign(previewWidget.value.params, params)
      if (!force_update &&
        !app.ui.settings.getSettingValue("VHS.AdvancedPreviews", false)) {
        return;
      }
      if (timeout) {
        clearTimeout(timeout);
      }
      if (force_update) {
        previewWidget.updateSource();
      } else {
        timeout = setTimeout(() => previewWidget.updateSource(), 100);
      }
    };
    previewWidget.updateSource = function () {
      if (this.value.params == undefined) {
        return;
      }
      let params = {}
      Object.assign(params, this.value.params);//shallow copy
      this.parentEl.hidden = this.value.hidden;
      if (params.format?.split('/')[0] == 'video' ||
        app.ui.settings.getSettingValue("VHS.AdvancedPreviews", false) &&
        (params.format?.split('/')[1] == 'gif') || params.format == 'folder') {
        this.videoEl.autoplay = !this.value.paused && !this.value.hidden;
        let target_width = 256
        if (element.style?.width) {
          //overscale to allow scrolling. Endpoint won't return higher than native
          target_width = element.style.width.slice(0, -2) * 2;
        }
        if (!params.force_size || params.force_size.includes("?") || params.force_size == "Disabled") {
          params.force_size = target_width + "x?"
        } else {
          let size = params.force_size.split("x")
          let ar = parseInt(size[0]) / parseInt(size[1])
          params.force_size = target_width + "x" + (target_width / ar)
        }
        if (app.ui.settings.getSettingValue("VHS.AdvancedPreviews", false)) {
          this.videoEl.src = api.apiURL('/viewvideo?' + new URLSearchParams(params));
        } else {
          previewWidget.videoEl.src = api.apiURL('/view?' + new URLSearchParams(params));
        }
        this.videoEl.hidden = false;
        this.imgEl.hidden = true;
      } else if (params.format?.split('/')[0] == 'image') {
        //Is animated image
        this.imgEl.src = api.apiURL('/view?' + new URLSearchParams(params));
        this.videoEl.hidden = true;
        this.imgEl.hidden = false;
      }
    }
    previewWidget.parentEl.appendChild(previewWidget.videoEl)
    previewWidget.parentEl.appendChild(previewWidget.imgEl)
  });
}

function addUploadWidget(nodeType, nodeData, widgetName, type = "video") {
  chainCallback(nodeType.prototype, "onNodeCreated", function () {
    const pathWidget = this.widgets.find((w) => w.name === widgetName);
    const fileInput = document.createElement("input");
    chainCallback(this, "onRemoved", () => {
      fileInput?.remove();
    });
    if (type == "video") {
      Object.assign(fileInput, {
        type: "file",
        accept: "video/webm,video/mp4,video/mkv,image/gif",
        style: "display: none",
        onchange: async () => {
          if (fileInput.files.length) {
            let resp = await uploadFile(fileInput.files[0])
            if (resp.status != 200) {
              //upload failed and file can not be added to options
              return;
            }
            const filename = (await resp.json()).name;
            pathWidget.options.values.push(filename);
            pathWidget.value = filename;
            if (pathWidget.callback) {
              pathWidget.callback(filename)
            }
          }
        },
      });
    } else {
      throw "Unknown upload type"
    }
    document.body.append(fileInput);
    let uploadWidget = this.addWidget("button", "choose " + type + " to upload", "image", () => {
      //clear the active click event
      app.canvas.node_widget = null

      fileInput.click();
    });
    uploadWidget.options.serialize = false;
  });
}

function addPreviewOptions(nodeType) {
  chainCallback(nodeType.prototype, "getExtraMenuOptions", function (_, options) {
    // The intended way of appending options is returning a list of extra options,
    // but this isn't used in widgetInputs.js and would require
    // less generalization of chainCallback
    let optNew = []
    const previewWidget = this.widgets.find((w) => w.name === "videopreview");

    let url = null
    if (previewWidget.videoEl?.hidden == false && previewWidget.videoEl.src) {
      //Use full quality video
      url = api.apiURL('/view?' + new URLSearchParams(previewWidget.value.params));
      //Workaround for 16bit png: Just do first frame
      url = url.replace('%2503d', '001')
    } else if (previewWidget.imgEl?.hidden == false && previewWidget.imgEl.src) {
      url = previewWidget.imgEl.src;
      url = new URL(url);
    }
    if (url) {
      optNew.push(
        {
          content: "Open preview",
          callback: () => {
            window.open(url, "_blank")
          },
        },
        {
          content: "Save preview",
          callback: () => {
            const a = document.createElement("a");
            a.href = url;
            a.setAttribute("download", new URLSearchParams(previewWidget.value.params).get("filename"));
            document.body.append(a);
            a.click();
            requestAnimationFrame(() => a.remove());
          },
        }
      );
    }
    const PauseDesc = (previewWidget.value.paused ? "Resume" : "Pause") + " preview";
    if (previewWidget.videoEl.hidden == false) {
      optNew.push({
        content: PauseDesc, callback: () => {
          //animated images can't be paused and are more likely to cause performance issues.
          //changing src to a single keyframe is possible,
          //For now, the option is disabled if an animated image is being displayed
          if (previewWidget.value.paused) {
            previewWidget.videoEl?.play();
          } else {
            previewWidget.videoEl?.pause();
          }
          previewWidget.value.paused = !previewWidget.value.paused;
        }
      });
    }
    //TODO: Consider hiding elements if no video preview is available yet.
    //It would reduce confusion at the cost of functionality
    //(if a video preview lags the computer, the user should be able to hide in advance)
    const visDesc = (previewWidget.value.hidden ? "Show" : "Hide") + " preview";
    optNew.push({
      content: visDesc, callback: () => {
        if (!previewWidget.videoEl.hidden && !previewWidget.value.hidden) {
          previewWidget.videoEl.pause();
        } else if (previewWidget.value.hidden && !previewWidget.videoEl.hidden && !previewWidget.value.paused) {
          previewWidget.videoEl.play();
        }
        previewWidget.value.hidden = !previewWidget.value.hidden;
        previewWidget.parentEl.hidden = previewWidget.value.hidden;
        fitHeight(this);

      }
    });
    optNew.push({
      content: "Sync preview", callback: () => {
        //TODO: address case where videos have varying length
        //Consider a system of sync groups which are opt-in?
        for (let p of document.getElementsByClassName("vhs_preview")) {
          for (let child of p.children) {
            if (child.tagName == "VIDEO") {
              child.currentTime = 0;
            } else if (child.tagName == "IMG") {
              child.src = child.src;
            }
          }
        }
      }
    });
    const muteDesc = (previewWidget.value.muted ? "Unmute" : "Mute") + " Preview"
    optNew.push({
      content: muteDesc, callback: () => {
        previewWidget.value.muted = !previewWidget.value.muted
      }
    })
    if (options.length > 0 && options[0] != null && optNew.length > 0) {
      optNew.push(null);
    }
    options.unshift(...optNew);
  });
}

function addLoadVideoCommon(nodeType, nodeData) {
  addVideoPreview(nodeType);
  addPreviewOptions(nodeType);
  chainCallback(nodeType.prototype, "onNodeCreated", function () {
    // const pathWidget = this.widgets.find((w) => w.name === "video");
    const pathWidget = this.widgets.find((w) => w.name === "default_value");
    //do first load
    requestAnimationFrame(() => {
      for (let w of [pathWidget]) {
        w.callback(w.value, null, this);
      }
    });
  });
}