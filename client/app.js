class WebSocketControlClient {
    constructor() {
        this.servers = this.loadServers();
        this.selectedServer = null;
        this.websocket = null;
        this.terminal = null;
        this.fitAddon = null;
        this.editingServerId = null;
        
        this.initializeElements();
        this.bindEvents();
        this.renderServerList();
        this.initializeTerminal();
    }
    
    initializeElements() {
        // 搜索和添加
        this.searchInput = document.getElementById('searchInput');
        this.addServerBtn = document.getElementById('addServerBtn');
        this.serverList = document.getElementById('serverList');
        this.actionPanel = document.getElementById('actionPanel');
        
        // 终端
        this.terminalContainer = document.getElementById('terminalContainer');
        this.welcomeMessage = document.getElementById('welcomeMessage');
        this.terminalElement = document.getElementById('terminal');
        
        // 文件操作
        this.uploadBtn = document.getElementById('uploadBtn');
        this.downloadBtn = document.getElementById('downloadBtn');
        
        // 对话框
        this.serverDialog = document.getElementById('serverDialog');
        this.uploadDialog = document.getElementById('uploadDialog');
        this.downloadDialog = document.getElementById('downloadDialog');
        
        // 服务器表单
        this.dialogTitle = document.getElementById('dialogTitle');
        this.serverNameInput = document.getElementById('serverName');
        this.serverAddressInput = document.getElementById('serverAddress');
        this.serverTokenInput = document.getElementById('serverToken');
        
        // 文件上传表单
        this.uploadFileInput = document.getElementById('uploadFile');
        this.uploadPathInput = document.getElementById('uploadPath');
        
        // 文件下载表单
        this.downloadPathInput = document.getElementById('downloadPath');
    }
    
    bindEvents() {
        // 搜索
        this.searchInput.addEventListener('input', () => this.renderServerList());
        
        // 添加服务器
        this.addServerBtn.addEventListener('click', () => this.showAddServerDialog());
        
        // 文件操作
        this.uploadBtn.addEventListener('click', () => this.showUploadDialog());
        this.downloadBtn.addEventListener('click', () => this.showDownloadDialog());
        
        // 对话框按钮
        document.getElementById('saveServerBtn').addEventListener('click', () => this.saveServer());
        document.getElementById('cancelServerBtn').addEventListener('click', () => this.hideServerDialog());
        
        document.getElementById('confirmUploadBtn').addEventListener('click', () => this.uploadFile());
        document.getElementById('cancelUploadBtn').addEventListener('click', () => this.hideUploadDialog());
        
        document.getElementById('confirmDownloadBtn').addEventListener('click', () => this.downloadFile());
        document.getElementById('cancelDownloadBtn').addEventListener('click', () => this.hideDownloadDialog());
        
        // 点击对话框外部关闭
        this.serverDialog.addEventListener('click', (e) => {
            if (e.target === this.serverDialog) this.hideServerDialog();
        });
        this.uploadDialog.addEventListener('click', (e) => {
            if (e.target === this.uploadDialog) this.hideUploadDialog();
        });
        this.downloadDialog.addEventListener('click', (e) => {
            if (e.target === this.downloadDialog) this.hideDownloadDialog();
        });
    }
    
    initializeTerminal() {
        this.terminal = new Terminal({
            theme: {
                background: '#0c0c0c',
                foreground: '#ffffff',
                cursor: '#ffffff'
            },
            fontSize: 14,
            fontFamily: 'Consolas, "Courier New", monospace',
            cursorBlink: true,
            scrollback: 1000
        });
        
        this.fitAddon = new FitAddon.FitAddon();
        this.terminal.loadAddon(this.fitAddon);
        
        this.terminal.onData(data => {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({
                    type: 'shell',
                    action: 'input',
                    data: data
                }));
            }
        });
        
        // 监听窗口大小变化
        window.addEventListener('resize', () => {
            if (this.terminalContainer.style.display !== 'none') {
                setTimeout(() => {
                    this.fitAddon.fit();
                    this.sendTerminalResize();
                }, 100);
            }
        });
    }
    
    sendTerminalResize() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            const { cols, rows } = this.terminal;
            this.websocket.send(JSON.stringify({
                type: 'shell',
                action: 'resize',
                cols: cols,
                rows: rows
            }));
        }
    }
    
    loadServers() {
        const stored = localStorage.getItem('servers');
        return stored ? JSON.parse(stored) : [];
    }
    
    saveServers() {
        localStorage.setItem('servers', JSON.stringify(this.servers));
    }
    
    renderServerList() {
        const searchTerm = this.searchInput.value.toLowerCase();
        const filteredServers = this.servers.filter(server => 
            server.name.toLowerCase().includes(searchTerm)
        );
        
        this.serverList.innerHTML = '';
        
        filteredServers.forEach(server => {
            const serverItem = document.createElement('div');
            serverItem.className = 'server-item';
            if (this.selectedServer && this.selectedServer.id === server.id) {
                serverItem.classList.add('selected');
            }
            
            serverItem.innerHTML = `
                <div class="server-name">${server.name}</div>
                <div class="server-address">${server.address}</div>
                <div class="server-actions">
                    <button class="server-action-btn edit-btn" data-id="${server.id}" title="编辑">✏️</button>
                    <button class="server-action-btn delete-btn" data-id="${server.id}" title="删除">🗑️</button>
                </div>
            `;
            
            serverItem.addEventListener('click', (e) => {
                if (!e.target.classList.contains('server-action-btn')) {
                    this.selectServer(server);
                }
            });
            
            // 绑定编辑和删除按钮
            serverItem.querySelector('.edit-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                this.editServer(server.id);
            });
            
            serverItem.querySelector('.delete-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteServer(server.id);
            });
            
            this.serverList.appendChild(serverItem);
        });
    }
    
    selectServer(server) {
        this.selectedServer = server;
        this.renderServerList();
        this.connectToServer();
    }
    
    connectToServer() {
        if (!this.selectedServer) return;
        
        this.disconnect();
        
        const [host, port] = this.selectedServer.address.split(':');
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${host}:${port}`;
        
        this.updateActionPanel('正在连接...');
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket连接已建立');
                this.updateActionPanel('正在认证...');
                this.authenticate();
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (e) {
                    console.error('解析消息失败:', e);
                }
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket连接已关闭');
                this.updateActionPanel('连接已断开');
                this.hideTerminal();
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket错误:', error);
                this.updateActionPanel('连接错误');
            };
            
        } catch (error) {
            console.error('连接失败:', error);
            this.updateActionPanel('连接失败');
        }
    }
    
    authenticate() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: 'auth',
                token: this.selectedServer.token
            }));
        }
    }
    
    handleMessage(data) {
        switch (data.type) {
            case 'auth_response':
                if (data.success) {
                    this.updateActionPanel('已连接');
                    this.showTerminal();
                    this.startShell();
                } else {
                    this.updateActionPanel(`认证失败: ${data.message}`);
                }
                break;
                
            case 'shell_started':
                console.log('Shell已启动');
                break;
                
            case 'shell_output':
                if (data.data) {
                    const output = atob(data.data);
                    this.terminal.write(output);
                }
                break;
                
            case 'shell_stopped':
                console.log('Shell已停止');
                break;
                
            case 'shell_error':
                console.error('Shell错误:', data.message);
                this.updateActionPanel(`Shell错误: ${data.message}`);
                break;
                
            case 'file_upload_response':
                alert(data.success ? data.message : `上传失败: ${data.message}`);
                break;
                
            case 'file_download_response':
                if (data.success) {
                    this.downloadFileContent(data.content, data.filename);
                } else {
                    alert(`下载失败: ${data.message}`);
                }
                break;
        }
    }
    
    startShell() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.terminal.clear();
            this.websocket.send(JSON.stringify({
                type: 'shell',
                action: 'start'
            }));
        }
    }
    
    showTerminal() {
        this.welcomeMessage.style.display = 'none';
        this.terminalContainer.style.display = 'flex';
        
        setTimeout(() => {
            this.terminal.open(this.terminalElement);
            this.fitAddon.fit();
            this.sendTerminalResize();
        }, 100);
    }
    
    hideTerminal() {
        this.terminalContainer.style.display = 'none';
        this.welcomeMessage.style.display = 'flex';
        this.terminal.reset();
    }
    
    updateActionPanel(text) {
        this.actionPanel.innerHTML = `<p>${text}</p>`;
    }
    
    disconnect() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
    }
    
    showAddServerDialog() {
        this.editingServerId = null;
        this.dialogTitle.textContent = '添加服务器';
        this.serverNameInput.value = '';
        this.serverAddressInput.value = '';
        this.serverTokenInput.value = '';
        this.serverDialog.style.display = 'flex';
    }
    
    editServer(id) {
        const server = this.servers.find(s => s.id === id);
        if (server) {
            this.editingServerId = id;
            this.dialogTitle.textContent = '编辑服务器';
            this.serverNameInput.value = server.name;
            this.serverAddressInput.value = server.address;
            this.serverTokenInput.value = server.token;
            this.serverDialog.style.display = 'flex';
        }
    }
    
    deleteServer(id) {
        if (confirm('确定要删除这个服务器吗？')) {
            this.servers = this.servers.filter(s => s.id !== id);
            if (this.selectedServer && this.selectedServer.id === id) {
                this.selectedServer = null;
                this.disconnect();
                this.hideTerminal();
                this.updateActionPanel('你还没有选中Server.');
            }
            this.saveServers();
            this.renderServerList();
        }
    }
    
    saveServer() {
        const name = this.serverNameInput.value.trim();
        const address = this.serverAddressInput.value.trim();
        const token = this.serverTokenInput.value.trim();
        
        if (!name || !address || !token) {
            alert('请填写所有字段');
            return;
        }
        
        if (this.editingServerId) {
            const server = this.servers.find(s => s.id === this.editingServerId);
            if (server) {
                server.name = name;
                server.address = address;
                server.token = token;
            }
        } else {
            const newServer = {
                id: Date.now().toString(),
                name: name,
                address: address,
                token: token
            };
            this.servers.push(newServer);
        }
        
        this.saveServers();
        this.renderServerList();
        this.hideServerDialog();
    }
    
    hideServerDialog() {
        this.serverDialog.style.display = 'none';
    }
    
    showUploadDialog() {
        this.uploadFileInput.value = '';
        this.uploadPathInput.value = '';
        this.uploadDialog.style.display = 'flex';
    }
    
    hideUploadDialog() {
        this.uploadDialog.style.display = 'none';
    }
    
    uploadFile() {
        const file = this.uploadFileInput.files[0];
        const path = this.uploadPathInput.value.trim();
        
        if (!file) {
            alert('请选择文件');
            return;
        }
        
        if (!path) {
            alert('请输入服务器保存路径');
            return;
        }
        
        const reader = new FileReader();
        reader.onload = (e) => {
            const content = e.target.result.split(',')[1]; // 移除data:*/*;base64,前缀
            
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({
                    type: 'file_upload',
                    path: path,
                    content: content
                }));
            }
        };
        reader.readAsDataURL(file);
        
        this.hideUploadDialog();
    }
    
    showDownloadDialog() {
        this.downloadPathInput.value = '';
        this.downloadDialog.style.display = 'flex';
    }
    
    hideDownloadDialog() {
        this.downloadDialog.style.display = 'none';
    }
    
    downloadFile() {
        const path = this.downloadPathInput.value.trim();
        
        if (!path) {
            alert('请输入服务器文件路径');
            return;
        }
        
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: 'file_download',
                path: path
            }));
        }
        
        this.hideDownloadDialog();
    }
    
    downloadFileContent(content, filename) {
        const blob = new Blob([atob(content)], { type: 'application/octet-stream' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename || 'download';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new WebSocketControlClient();
});