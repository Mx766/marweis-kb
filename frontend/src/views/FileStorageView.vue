<template>
  <div class="drive-page"
  @drop.prevent="onDrop" @dragover.prevent="onDragOver" @dragenter.prevent="onDragEnter" @dragleave.prevent="onDragLeave">
  <!-- 全屏拖拽覆盖层 -->
  <div v-if="dragOver" class="drag-overlay">
    <el-icon :size="48"><Upload /></el-icon>
    <p>释放文件以上传</p>
  </div>
    <!-- ====== MODE 1: Admin Overview ====== -->
    <div v-if="mode==='overview'" class="overview">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
        <button class="btn" @click="router.push('/')"><el-icon :size="14"><ArrowLeft /></el-icon> 返回</button>
        <h2 class="ov-title" style="margin:0">📊 共享盘概览</h2>
      </div>
      <div class="dept-grid">
        <div v-for="d in overview.dept_stats" :key="d.department" class="dept-card"
          :style="{borderTopColor: DEPT_CONFIG[d.department]?.color||'#999'}"
          @click="enterDept(d.department)">
          <div class="dc-header">
            <span class="dc-dot" :style="{background:DEPT_CONFIG[d.department]?.color||'#999'}"></span>
            <span class="dc-name">{{ d.department }}</span>
          </div>
          <div class="dc-stats">
            <div class="dc-stat"><strong>{{ d.count }}</strong> 文件</div>
            <div class="dc-stat"><strong>{{ formatSize(d.size) }}</strong></div>
          </div>
          <div class="dc-footer" v-if="d.last_active">{{ formatDate(d.last_active) }}</div>
        </div>
      </div>

      <!-- 最近上传 -->
      <div class="ov-section" v-if="overview.recent?.length">
        <h3>🕐 最近上传</h3>
        <div class="recent-list">
          <div v-for="f in overview.recent" :key="f.id" class="recent-row"
            @click="openRecent(f)">
            <span class="recent-icon">{{ iconForExt(f.file_ext) }}</span>
            <span class="recent-name">{{ f.filename }}</span>
            <span class="recent-dept" :style="{color:DEPT_CONFIG[f.department]?.color}">{{ f.department }}</span>
            <span class="recent-user">{{ f.uploader_name }}</span>
            <span class="recent-time">{{ timeAgo(f.updated_at) }}</span>
          </div>
        </div>
      </div>

      <!-- 入口按钮 -->
      <div class="ov-actions">
        <button class="act-btn" @click="enterMy"><span>📂</span> 我的私盘 ({{ overview.my_count }})</button>
        <button class="act-btn" @click="goTrash()"><span>🗑</span> 回收站 ({{ overview.trash_count }})</button>
      </div>
    </div>

    <!-- ====== MODE 2: File Browser ====== -->
    <template v-else>
      <aside class="drive-sidebar">
        <div class="side-hd">团队公盘</div>

        <template v-if="(browseMode && browseMode!=='my') || sharedView">
          <div class="side-section-title">📂 公盘</div>
          <div class="side-item" :class="{active: !currentFolder && !sharedView}"
            @click="goAllFiles()">
            <el-icon :size="16"><FolderOpened /></el-icon> 全部文件
          </div>
          <div class="side-divider"></div>
          <div class="side-section-title">👤 我的私盘</div>
          <div class="side-item" :class="{active: browseMode==='my'}"
            @click="enterMy()">
            <el-icon :size="16"><User /></el-icon> 我的私盘
          </div>
          <div class="side-divider"></div>
          <div class="side-section-title" v-if="!auth.isSuperAdmin">🔗 跨部门共享</div>
          <div class="side-item" v-if="!auth.isSuperAdmin" :class="{active: sharedView}"
            @click="enterShared()">
            <el-icon :size="16"><Link /></el-icon> 共享给我
          </div>
          <div class="side-section-title">📨 文件传输</div>
          <div class="side-item" @click="openTransfers()">
            <el-icon :size="16"><Message /></el-icon> 收到的传输
            <span v-if="incomingCount" class="dept-count">{{ incomingCount }}</span>
          </div>
          <div class="side-item" @click="openSent()">
            <el-icon :size="16"><Promotion /></el-icon> 发出的传输
          </div>
          <div class="side-item" :class="{active: mode==='stars'}" @click="goStars()">
            <el-icon :size="16"><Star /></el-icon> 星标文件
          </div>
          <template v-if="auth.isAdmin">
            <div class="side-divider"></div>
            <div class="side-section-title">👥 员工私盘</div>
            <div class="side-item" v-for="u in deptUsers" :key="u.user_id"
              :class="{active: viewEmployee?.id===u.user_id}"
              @click="enterEmployeePrivate(u)">
              <el-icon :size="16"><User /></el-icon> {{ u.name }}
              <span class="dept-count">{{ u.count }}</span>
            </div>
          </template>
        </template>
        <template v-else-if="browseMode==='my'">
          <div class="side-section-title">📂 我的私盘</div>
          <div class="side-divider"></div>
          <div class="side-item" :class="{active: false}"
            @click="backToDrive()">
            <el-icon :size="16"><FolderOpened /></el-icon> 返回公盘
          </div>
        </template>

        <!-- Overview: show dept drives -->
        <template v-else>
          <div class="side-section-title">📂 公盘</div>
          <div class="side-item dept-item" v-for="d in deptList" :key="d.name"
            :class="{active: browseMode===d.name}"
            @click="enterDept(d.name)">
            <span class="dept-dot" :style="{background:d.color}"></span>{{ d.name }}
          </div>
        </template>

        <div class="side-divider"></div>
        <div class="side-item trash" :class="{active: mode==='trash'}"
          @click="goTrash()">
          <el-icon :size="16"><Delete /></el-icon> 回收站
        </div>
        <div class="side-stats">
          <div class="stat-label">已用 {{ formatSize(statsSize) }}</div>
          <div class="stat-bar"><div class="stat-fill" :style="{width:usagePct+'%'}"></div></div>
        </div>
      </aside>

      <main class="drive-main">
        <!-- Header -->
        <div class="browse-header">
          <button class="btn" @click="goBackFolder()"><el-icon :size="14"><ArrowLeft /></el-icon> 返回</button>
          <div class="browse-title">
            <span class="browse-icon">{{ browseMode==='my' ? '📂' : '📁' }}</span>
            <span class="browse-name">{{ sharedView ? '跨部门共享' : (viewEmployee ? (viewEmployee.name+' 的私盘') : (browseMode==='my' ? '我的私盘' : browseMode)) }}</span>
            <span v-if="!sharedView && currentFolder && breadcrumb.length>2" class="browse-bread">
              <span v-for="(b,i) in breadcrumb.slice(2)" :key="b.id||'r'" class="bc-seg" @click="currentFolder=b.id;doLoad()">/ {{ b.name }}</span>
            </span>
          </div>
          <div class="browse-stats" v-if="!trashView">
            <span>{{ total }} 个项目</span>
            <span v-if="statsSize">· {{ formatSize(statsSize) }}</span>
          </div>
        </div>

        <!-- Toolbar -->
        <div class="browse-toolbar" v-if="!trashView">
          <input ref="fInp" type="file" multiple hidden @change="onUpload" />
          <input ref="fDirInp" type="file" webkitdirectory directory hidden @change="onUpload" />
          <button v-if="!viewEmployee && !sharedView" class="btn-primary" @click="uploadOpen=true;loadUsersTree()"><el-icon :size="16"><Upload /></el-icon> 上传</button>
          <button v-if="!viewEmployee && !sharedView" class="btn" @click="showNewFolder"><el-icon :size="16"><FolderAdd /></el-icon> 新建文件夹</button>
          <button v-if="!viewEmployee && !sharedView" class="btn" @click="exportManifest" title="导出当前文件夹文件清单，用于完整性核对"><el-icon :size="14"><Download /></el-icon> 导出清单</button>
          <span class="tb-sep" v-if="selected.length"></span>
          <span class="tb-count" v-if="selected.length">已选 {{ selected.length }} 项</span>
          <button class="btn danger" v-if="selected.length && !viewEmployee && selectedCanWrite" @click="batchTrash"><el-icon :size="16"><Delete /></el-icon> 删除({{selected.length}})</button>
          <button class="btn" v-if="selected.length" @click="batchDownload"><el-icon :size="16"><Download /></el-icon> 下载({{selected.length}})</button>
          <button class="btn" v-if="selected.length && !viewEmployee && selectedCanWrite" @click="moveVisible=true"><el-icon :size="16"><Switch /></el-icon> 移动到</button>
          <button class="btn" v-if="selected.length" @click="openSendMulti()"><el-icon :size="16"><Promotion /></el-icon> 发送({{selected.length}})</button>
          <div class="tb-right">
            <select v-model="fileTypeFilter" class="search-inp" style="width:116px" @change="onTypeFilter">
              <option value="">全部类型</option>
              <option value="doc">📄 文档</option>
              <option value="sheet">📊 表格</option>
              <option value="image">🖼 图片</option>
              <option value="video">🎬 视频</option>
              <option value="audio">🎵 音频</option>
              <option value="other">📦 其他</option>
            </select>
            <input v-model="keyword" class="search-inp" placeholder="搜索文件..." @input="onSearch" />
            <button class="btn" :class="{active:treeMode}" @click="toggleTree" :title="treeMode?'切换到文件列表':'文件夹树（核对完整性）'"><el-icon :size="14"><FolderOpened /></el-icon> 树状</button>
            <button class="btn" :class="{active:view==='grid'}" @click="view='grid'"><el-icon :size="14"><Grid /></el-icon></button>
            <button class="btn" :class="{active:view==='list'}" @click="view='list'"><el-icon :size="14"><List /></el-icon></button>
          </div>
        </div>
        <div class="browse-toolbar" v-else>
          <button class="btn" @click="goBrowse()"><el-icon :size="16"><ArrowLeft /></el-icon> 返回文件</button>
          <button class="btn" v-if="selected.length" @click="batchRestore">恢复({{selected.length}})</button>
          <button class="btn danger" v-if="auth.isSuperAdmin && selected.length" @click="batchDeletePermanent">彻底删除</button>
          <button class="btn danger" v-if="files.length && auth.isAdmin" @click="emptyTrash" style="margin-left:auto">清空回收站</button>
        </div>

        <!-- Upload progress -->
        <div v-if="uploading.length" class="up-queue">
          <div v-for="u in uploading" :key="u.name" class="up-row"><span>{{ u.name }}</span><span v-if="u.total" class="up-info">{{ u.done||0 }}/{{ u.total }}</span><el-progress :percentage="u.pct" :status="u.err?'exception':u.pct===100?'success':undefined" :stroke-width="8" style="width:200px" /></div>
        </div>


        <!-- Table head -->
        <div class="drive-head" v-if="!treeMode && files.length && view==='list'">
          <div class="h-check"><input type="checkbox" @change="toggleAll" :checked="allSelected" /></div>
          <div class="h-name" @click="sortBy='name';doLoad()">名称 <span v-if="sortBy==='name'">↑</span></div>
          <div class="h-size" @click="sortBy='size';doLoad()">大小 <span v-if="sortBy==='size'">↑</span></div>
          <div class="h-type">类型</div>
          <div class="h-date" @click="sortBy='date';doLoad()">修改 <span v-if="sortBy==='date'">↑</span></div>
          <div class="h-uploader">上传者</div>
          <div class="h-act">操作</div>
        </div>

        <!-- Loading: 仅首次/空列表时显示；切换目录保留旧列表避免闪烁 -->
        <div v-if="loading && !files.length" class="loading-tip">加载中…</div>

        <!-- 文件夹树视图（完整性核对） -->
        <div v-if="treeMode && !trashView && !sharedView" class="tree-panel">
          <div class="tree-panel-hd">
            <el-icon :size="14"><FolderOpened /></el-icon> 文件夹树
            <span class="tree-panel-sub">每个文件夹显示“文件数 · 大小”，可与本地文件夹属性比对</span>
            <span class="tree-refresh" @click="loadFolderTree()">刷新</span>
          </div>
          <el-tree
            class="main-folder-tree"
            :data="folderTree"
            :props="{label:'name', children:'children'}"
            node-key="id"
            default-expand-all
            :highlight-current="true"
            :current-node-key="currentFolder || undefined"
            @node-click="onTreeClick"
          >
            <template #default="{ data }">
              <span class="tree-node">
                <el-icon :size="15" style="color:#f59e0b"><Folder /></el-icon>
                <span class="tree-node-name">{{ data.name }}</span>
                <span class="tree-node-count">{{ data.child_count ?? 0 }} 个文件 · {{ formatSize(data.child_size || 0) }}</span>
              </span>
            </template>
          </el-tree>
        </div>

        <!-- Grid view -->
        <div v-if="!treeMode && view==='grid'" class="drive-grid">
          <div v-for="f in files" :key="f.id" class="g-item" :class="{sel:selected.includes(f.id)}" @click="onClick(f,$event)" @dblclick="openItem(f)" draggable="true" @dragstart="dragItem=f" @dragend="dragItem=null" @contextmenu.prevent>
            <div class="g-check" @click.stop><input type="checkbox" :checked="selected.includes(f.id)" @change="toggleOne(f.id)" /></div>
            <div class="g-icon" :style="{color:iconColor(f.file_ext)}"><el-icon :size="40"><component :is="f.is_folder?Folder:Document" /></el-icon></div>
            <div class="g-name" :title="f.filename">{{ f.filename }}</div>
            <div class="g-meta">{{ f.is_folder ? folderSummary(f) : formatSize(f.file_size) }}</div>
          </div>
        </div>
        <div v-if="!treeMode && view==='grid' && !files.length" class="drive-empty"><el-icon :size="48"><component :is="trashView?Delete:FolderOpened" /></el-icon><p>{{ trashView?'回收站为空':'暂无文件，点击上方"上传"添加' }}</p></div>

        <!-- List view -->
        <div v-if="!treeMode && view==='list'" class="drive-list">
          <div v-for="f in files" :key="f.id" class="l-row" :class="{sel:selected.includes(f.id)}" @click="onClick(f,$event)" @dblclick="openItem(f)" draggable="true" @dragstart="dragItem=f" @dragend="dragItem=null" @contextmenu.prevent>
            <div class="l-check" @click.stop><input type="checkbox" :checked="selected.includes(f.id)" @change="toggleOne(f.id)" /></div>
            <div class="l-name"><el-icon :size="18" :style="{color:f.is_folder?'#f59e0b':iconColor(f.file_ext)}"><component :is="f.is_folder?Folder:Document" /></el-icon><span :title="f.filename">{{ f.filename }}</span><span v-if="!f.is_folder && !canDownload(f)" class="dl-lock" title="未开放员工下载">🔒</span></div>
            <div class="l-size">{{ f.is_folder ? folderSummary(f) : formatSize(f.file_size) }}</div>
            <div class="l-type">{{ f.is_folder?'文件夹':(f.file_ext||'?').toUpperCase() }}</div>
            <div class="l-date">{{ formatDate(f.updated_at) }}</div>
            <div class="l-uploader">{{ f.uploader_name||'-' }}</div>
            <div class="l-act" @click.stop>
              <el-button v-if="!f.is_folder" size="small" :icon="f.starred ? StarFilled : Star" text
                :type="f.starred ? 'warning' : 'default'" @click="toggleStar(f)"
                :title="f.starred ? '取消星标' : '星标收藏（常用文件置顶）'" />
              <el-button v-if="!f.is_folder && canDownload(f)" size="small" :icon="Download" text @click="doDownload(f)" title="下载" />
              <el-button size="small" :icon="Promotion" @click="openSendDialog(f)" title="发送给同事（文件夹自动打包为内部文件），对方接收后进入其私盘">发送</el-button>
              <el-button v-if="!viewEmployee && f.can_write" size="small" :icon="Delete" text @click="doTrash(f)" title="删除" />
              <el-dropdown trigger="click" size="small" @command="(cmd: any) => onRowCmd(cmd, f)">
                <el-button size="small" :icon="MoreFilled" text title="更多操作" />
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item v-if="!f.is_folder && canDownload(f)" command="share">生成分享链接</el-dropdown-item>
                    <el-dropdown-item v-if="!f.is_folder && (isOffice(f.file_ext) || isImage(f.file_ext) || isVideo(f.file_ext) || isAudio(f.file_ext))" command="preview">预览</el-dropdown-item>
                    <el-dropdown-item v-if="!viewEmployee && f.can_write" command="rename">重命名</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </div>
        <div v-if="!treeMode && view==='list' && !files.length" class="drive-empty"><el-icon :size="48"><component :is="trashView?Delete:FolderOpened" /></el-icon><p>{{ trashView?'回收站为空':'暂无文件，点击上方"上传"添加' }}</p></div>

        <div class="drive-foot" v-if="total>size"><el-pagination v-model:current-page="page" :page-size="size" :total="total" layout="total, prev, pager, next" small @current-change="onPageChange" /></div>
      </main>

      <!-- Dialogs -->
      <el-dialog v-model="newFolderVisible" title="新建文件夹" width="360px"><el-input v-model="newFolderName" placeholder="文件夹名称" @keyup.enter="createFolder" /><template #footer><el-button @click="newFolderVisible=false">取消</el-button><el-button type="primary" @click="createFolder">创建</el-button></template></el-dialog>
      <el-dialog v-model="renameVisible" title="重命名" width="360px"><el-input v-model="renameName" @keyup.enter="doRename" />
        <div style="margin-top:10px;display:flex;align-items:center;gap:6px" v-if="renameTarget && !renameTarget.is_folder">
          <el-switch v-model="renameEmpDownload" size="small" /><span style="font-size:12px;color:#666">允许员工下载</span>
        </div>
        <template #footer><el-button @click="renameVisible=false">取消</el-button><el-button type="primary" @click="doRename">确定</el-button></template></el-dialog>
      <el-dialog v-model="previewShow" :title="previewFile?.filename" width="85%" top="2vh" @close="previewFile=null;previewUrl='';previewShow=false">
        <div style="text-align:center">
          <img v-if="previewUrl && isImage(previewFile?.file_ext)" :src="previewUrl" style="max-width:100%;max-height:70vh" />
          <video v-else-if="previewUrl && isVideo(previewFile?.file_ext)" :src="previewUrl" controls autoplay style="max-width:100%;max-height:70vh" />
          <audio v-else-if="previewUrl && isAudio(previewFile?.file_ext)" :src="previewUrl" controls style="width:100%;max-width:640px" />
        </div>
        <div style="text-align:center;margin-top:8px" v-if="previewFile">
          <template v-if="isImage(previewFile?.file_ext)">
            <el-button size="small" :disabled="!hasPrev" @click="previewStep(-1)">上一张</el-button>
            <span style="margin:0 10px;font-size:12px;color:#888">{{ previewIdx + 1 }} / {{ imageFiles.length }}</span>
            <el-button size="small" :disabled="!hasNext" @click="previewStep(1)">下一张</el-button>
          </template>
          <el-button size="small" :icon="Download" @click="doDownload(previewFile)">下载</el-button>
        </div>
      </el-dialog>
      <el-dialog v-model="moveVisible" title="移动到" width="400px"><div class="move-list"><div class="move-item" @click="doMove(null)">📁 根目录</div><div v-for="f in allFolders" :key="f.id" class="move-item" @click="doMove(f.id)">📁 {{ f.filename }}</div></div></el-dialog>
      <el-dialog v-model="share.open" title="分享文件" width="500px">
        <div class="share-row">
          <span>有效期</span>
          <el-select v-model="share.days" style="width: 120px" @change="refreshShareUrl">
            <el-option :value="1" label="1 天" />
            <el-option :value="7" label="7 天" />
            <el-option :value="30" label="30 天" />
          </el-select>
        </div>
        <div class="share-box"><code>{{ share.url || '生成中…' }}</code></div>
        <p class="share-tip">链接无需登录即可下载，请勿对外随意传播。</p>
        <template #footer>
          <el-button @click="share.open = false">关闭</el-button>
          <el-button type="primary" :disabled="!share.url" @click="copyShare">复制链接</el-button>
        </template>
      </el-dialog>

      <!-- 上传对话框：选择来源 + 可见范围 + 下载开关 -->
      <el-dialog v-model="uploadOpen" title="上传文件" width="620px" top="6vh" @close="pendingFiles=[];pendingDirs=[];pendingDirCount=0">
        <div class="up-src-row">
          <button class="btn-primary" @click="pickFiles()"><el-icon :size="14"><Upload /></el-icon> 选择文件</button>
          <button class="btn" @click="pickFolder()"><el-icon :size="14"><FolderAdd /></el-icon> 选择文件夹</button>
          <span class="up-src-tip">也可直接把文件/文件夹拖到公盘页面</span>
        </div>
        <div v-if="pendingFiles.length" class="up-manifest">
          <div class="up-manifest-hd">
            待上传清单：{{ pendingFiles.length }} 个文件 · {{ formatSize(pendingTotalSize) }}
            <span v-if="pendingDirCount"> · {{ pendingDirCount }} 个文件夹</span>
            <span class="tree-refresh" @click="pendingFiles=[];pendingDirs=[];pendingDirCount=0">清空</span>
          </div>
          <div class="up-manifest-list">
            <div v-for="g in pendingGroups" :key="g.name" class="up-manifest-group">
              <div class="up-manifest-group-hd">
                <span>{{ g.isFile ? '📄' : '📁' }} {{ g.name }}</span>
                <span class="up-m-size">{{ g.count }} 个 · {{ formatSize(g.size) }}</span>
              </div>
              <div v-for="(pf, i) in g.files.slice(0, 5)" :key="i" class="up-manifest-row">
                <span class="up-m-name" :title="pf.rel || pf.file.name">{{ g.isFile ? pf.file.name : pf.rel }}</span>
                <span class="up-m-size">{{ formatSize(pf.file.size) }}</span>
              </div>
              <div v-if="g.files.length > 5" class="up-manifest-more">… 该目录共 {{ g.files.length }} 个文件</div>
            </div>
          </div>
        </div>
        <div v-else class="up-manifest-empty">尚未选择文件/文件夹</div>

        <div class="scope-panel" style="margin-top:12px">
          <div class="scope-title">可见范围（谁可以看到这些文件）</div>
          <el-radio-group v-model="uploadScopeSel" size="small">
            <el-radio value="dept">本部门员工可见</el-radio>
            <el-radio value="admin">仅本部门管理员可见</el-radio>
            <el-radio value="specific">指定部门</el-radio>
            <el-radio value="users">指定人员</el-radio>
          </el-radio-group>
          <el-tree
            v-if="uploadScopeSel==='specific'"
            class="scope-tree"
            :data="deptTreeData"
            show-checkbox
            node-key="name"
            :default-expand-all="true"
            :props="{label:'name'}"
            @check="onDeptCheck"
          />
          <el-tree
            v-if="uploadScopeSel==='users'"
            class="scope-tree"
            :data="usersTreeData"
            show-checkbox
            node-key="id"
            :default-expand-all="false"
            :props="{label:'name', children:'children'}"
            @check="onUsersCheck"
          />
        </div>
        <div class="dl-switch" style="margin-top:10px">
          <el-switch v-model="allowEmpDownload" size="small" />
          <span>允许员工下载（关闭后其他员工只能在线预览，不能下载）</span>
        </div>
        <template #footer>
          <el-button @click="uploadOpen=false">取消</el-button>
          <el-button type="primary" :disabled="!pendingFiles.length || uploading.length > 0" @click="startUpload">开始上传</el-button>
        </template>
      </el-dialog>

      <!-- 上传结果 -->
      <el-dialog v-model="uploadResult.open" title="上传结果" width="460px">
        <p class="up-result-ok">✅ 成功 {{ uploadResult.ok }} 个</p>
        <template v-if="uploadResult.integrity">
          <p class="up-result-ok" :style="uploadResult.integrity.ok ? {} : {color:'#e6a23c'}">
            🛡 完整性对比：{{ uploadResult.integrity.message }}
          </p>
          <div v-if="uploadResult.integrity.missing.length">
            <p class="up-result-fail">少了 {{ uploadResult.integrity.missing.length }} 个：</p>
            <div class="up-result-list">
              <div v-for="(n, i) in uploadResult.integrity.missing" :key="i">{{ n.name }}</div>
            </div>
          </div>
          <div v-if="uploadResult.integrity.extra.length">
            <p style="color:#e6a23c;font-size:13px;margin:6px 0">服务器上多了 {{ uploadResult.integrity.extra.length }} 个（可能为原有文件）：</p>
            <div class="up-result-list">
              <div v-for="(n, i) in uploadResult.integrity.extra" :key="i">{{ n.name }}</div>
            </div>
          </div>
        </template>
        <div v-if="uploadResult.fail.length">
          <p class="up-result-fail">❌ 失败/跳过 {{ uploadResult.fail.length }} 个：</p>
          <div class="up-result-list">
            <div v-for="(n, i) in uploadResult.fail" :key="i">{{ n }}</div>
          </div>
        </div>
        <template #footer>
          <el-button @click="uploadResult.open=false">关闭</el-button>
        </template>
      </el-dialog>

      <!-- 发送文件给同事 -->
      <el-dialog v-model="sendOpen" :title="'发送文件' + (sendTargets.length > 1 ? `（${sendTargets.length} 项）` : '')" width="520px">
        <div class="send-file-name" v-if="sendTargets.length === 1">
          {{ sendTargets[0].is_folder ? '📁' : '📄' }} {{ sendTargets[0].filename }}
        </div>
        <div class="send-file-list" v-else-if="sendTargets.length">
          <div v-for="t in sendTargets.slice(0, 30)" :key="t.id" class="send-file-item">
            {{ t.is_folder ? '📁' : '📄' }} {{ t.filename }}
            <span v-if="t.is_folder" style="color:#999;font-size:12px">（文件夹，发送其全部文件）</span>
          </div>
          <div v-if="sendTargets.length > 30" style="color:#999;font-size:12px;margin-top:4px">
            等共 {{ sendTargets.length }} 项
          </div>
        </div>
        <div class="send-user-tree">
          <el-input v-model="sendKeyword" size="small" placeholder="搜索同事姓名..." style="margin-bottom:6px" clearable />
          <el-tree
            class="scope-tree"
            :data="sendTreeData"
            node-key="id"
            :props="{label:'name', children:'children'}"
            highlight-current
            :expand-on-click-node="false"
            @node-click="onSendUserClick"
          />
        </div>
        <el-input v-model="sendMessage" type="textarea" :rows="2" maxlength="500" show-word-limit placeholder="附言（可选）" style="margin-top:8px" />
        <template #footer>
          <el-button @click="sendOpen=false">取消</el-button>
          <el-button type="primary" :disabled="!sendTargets.length || !sendToUser" @click="doSendFile">发送</el-button>
        </template>
      </el-dialog>

      <!-- 收到的传输 -->
      <el-dialog v-model="transfersOpen" title="收到的文件传输" width="560px">
        <div v-if="incoming.length===0" class="up-manifest-empty">暂无待处理的传输</div>
        <div v-for="t in incoming" :key="t.id" class="transfer-row">
          <div class="transfer-info">
            <div class="transfer-name">📄 {{ t.filename }} <span class="transfer-size">{{ formatSize(t.file_size) }}</span></div>
            <div class="transfer-meta">来自 {{ t.from_name }} · {{ timeAgo(t.created_at) }}<span v-if="t.message"> · {{ t.message }}</span></div>
          </div>
          <div class="transfer-acts">
            <el-button size="small" type="primary" @click="doAccept(t)">接收</el-button>
            <el-button size="small" @click="doReject(t)">拒绝</el-button>
          </div>
        </div>
      </el-dialog>

      <!-- 发出的传输（历史 + 撤回） -->
      <el-dialog v-model="sentOpen" title="发出的传输" width="620px">
        <div v-if="sentList.length===0" class="up-manifest-empty">还没有发出过传输</div>
        <div v-for="t in sentList" :key="t.id" class="transfer-row">
          <div class="transfer-info">
            <div class="transfer-name">📄 {{ t.filename }} <span class="transfer-size">{{ formatSize(t.file_size) }}</span></div>
            <div class="transfer-meta">
              发给 {{ t.to_name }} · {{ timeAgo(t.created_at) }}
              <el-tag size="small" :type="t.status==='accepted' ? 'success' : (t.status==='pending' ? 'warning' : (t.status==='rejected' ? 'danger' : 'info'))" style="margin-left:6px">
                {{ t.status==='pending' ? '待接收' : t.status==='accepted' ? '已接收' : t.status==='rejected' ? '已拒绝' : '已撤回' }}
              </el-tag>
            </div>
          </div>
          <div class="transfer-acts">
            <el-button v-if="t.status==='pending'" size="small" type="danger" @click="doRevoke(t)">撤回</el-button>
          </div>
        </div>
      </el-dialog>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Folder, FolderOpened, FolderAdd, Document, Upload, Download, Delete, Grid, List, ArrowLeft, Switch, EditPen, View, User, Link, Message, Promotion, Star, StarFilled, MoreFilled } from '@element-plus/icons-vue'
import { get, upload, post, del, put } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const fInp = ref<any>(null)
const fDirInp = ref<any>(null)
const QUOTA = 10*1024*1024*1024

const DEPT_CONFIG: Record<string,{icon:string;color:string}> = {
  '总经办':{icon:'E',color:'#1e40af'},'人力资源部':{icon:'H',color:'#d97706'},
  '财务部':{icon:'F',color:'#65a30d'},'市场部':{icon:'M',color:'#ec4899'},
  '注册部':{icon:'R',color:'#1e50ae'},'医学部':{icon:'Y',color:'#2e86c1'},
  '临床运营部':{icon:'S',color:'#0891b2'},'临床研究部':{icon:'C',color:'#059669'},
  '质量部':{icon:'Q',color:'#a855f7'},'商务部':{icon:'B',color:'#2563eb'},
  '国际部':{icon:'K',color:'#e11d48'},'公共共享区':{icon:'S',color:'#6366f1'},
}
const DEPT_NAMES = Object.keys(DEPT_CONFIG)

// 视图模式: overview | entry | browse | trash
const mode = ref('')
const browseMode = ref('') // 'my' or dept name
const sharedView = ref(false) // 跨部门共享视图
const prevBrowseMode = ref('') // 进入“我的文件”前的浏览位置，用于返回
const files = ref<any[]>([]); const breadcrumb = ref<any[]>([]); const allFolders = ref<any[]>([])
const statsSize = ref(0)
const currentFolder = ref<string|null>(null)
const keyword = ref(''); const sortBy = ref('name')
function defaultView() {
  return (typeof window !== 'undefined' && window.innerWidth <= 600) ? 'grid' : 'list'
}
const view = ref(defaultView())
const page = ref(1); const size = ref(50); const total = ref(0); const selected = ref<string[]>([])
const uploading = ref<any[]>([]); const dragItem = ref<any>(null); const dragOver = ref(false)
const allowEmpDownload = ref(true)
const uploadScopeSel = ref<'dept'|'admin'|'all'|'specific'|'users'>('dept')
const uploadDepts = ref<string[]>([])
const uploadUserIds = ref<string[]>([])
const usersTreeData = ref<any[]>([])
const folderTree = ref<any[]>([])
const treeLoading = ref(false)
const deptTreeData = computed(() => DEPT_NAMES.map(n => ({name: n})))
const uploadOpen = ref(false)
const pendingFiles = ref<{file: File; rel: string}[]>([])
const pendingDirs = ref<{dir: boolean; rel: string}[]>([])
const pendingDirCount = ref(0)
const pendingTotalSize = computed(() => pendingFiles.value.reduce((s, p) => s + (p.file.size || 0), 0))
const pendingGroups = computed(() => {
  const groups: Record<string, any> = {}
  for (const pf of pendingFiles.value) {
    const rel = pf.rel || pf.file.name
    const isFolderFile = rel.includes('/')
    const root = isFolderFile ? rel.split('/')[0] : pf.file.name
    if (!groups[root]) groups[root] = {name: root, isFile: !isFolderFile, files: [], size: 0}
    groups[root].files.push(pf)
    groups[root].size += pf.file.size || 0
  }
  return Object.values(groups).map(g => ({...g, count: g.files.length}))
})
const uploadResult = ref<{open: boolean; ok: number; fail: string[]; integrity?: any}>({open: false, ok: 0, fail: []})
const treeMode = ref(false)
const sendOpen = ref(false)
const sendTargets = ref<any[]>([])
const sendToUser = ref<any>(null)
const sendMessage = ref('')
const sendKeyword = ref('')
const transfersOpen = ref(false)
const incoming = ref<any[]>([])
const incomingCount = ref(0)
const sentOpen = ref(false)
const sentList = ref<any[]>([])
const fileTypeFilter = ref('')
let lastIncomingCount = -1
let incomingTimer: any = null
const seenTransferIds = new Set<string>()
let dragDepth = 0

function onDragOver() { if (!dragItem.value) dragOver.value = true }
function onDragEnter() { if (!dragItem.value) { dragDepth++; dragOver.value = true } }
function onDragLeave() { dragDepth--; if (dragDepth <= 0) { dragDepth = 0; dragOver.value = false } }
const loading = ref(false)
const newFolderVisible = ref(false); const newFolderName = ref('')
const moveVisible = ref(false)
const allSelected = computed(() => files.value.length>0 && selected.value.length===files.value.length)
const selectedCanWrite = computed(() => {
  if (!selected.value.length) return false
  return selected.value.every((id: string) => {
    const f = files.value.find((x: any) => x.id === id)
    return f ? f.can_write !== false : false
  })
})
const trashView = computed(() => mode.value === 'trash')
const usagePct = computed(() => Math.min(100, statsSize.value/QUOTA*100))
// Map dept name → folder ID from overview data
const deptRootId = computed(() => {
  const info = overview.value.dept_stats?.find((d:any)=>d.department===browseMode.value)
  return info?.folder_id || ''
})
let _t: any = null

const overview = ref<any>({dept_stats:[],recent:[],my_count:0,my_size:0,trash_count:0})
const deptList = ref<{name:string;color:string}[]>([])
const subfolders = ref<any[]>([])
const deptUsers = ref<{user_id:string;name:string;count:number}[]>([])
const uploaderFilter = ref('')
const viewEmployee = ref<{id:string;name:string}|null>(null)
// 性能缓存：部门成员/统计/子文件夹只在变化时请求，避免每次操作重复拉取
const deptUsersCache: Record<string, any[]> = {}
let statsLoaded = false
let lastSubKey = ''

function formatSize(b: number) { if(!b) return '-'; const u=['B','KB','MB','GB']; let i=0,v=b; while(v>=1024&&i<3){v/=1024;i++}; return v.toFixed(1)+' '+u[i] }
function folderSummary(f: any) {
  if (f.child_count == null) return '-'
  if (f.child_count === 0) return '空文件夹'
  return `${f.child_count} 个文件 · ${formatSize(f.child_size)}`
}
function formatDate(d: string) { return d?dayjs(d).format('MM-DD HH:mm'):'' }
function timeAgo(d: string) { if(!d) return ''; const diff=Date.now()-new Date(d).getTime(); const m=Math.floor(diff/60000); if(m<1) return '刚刚'; if(m<60) return m+'分钟前'; const h=Math.floor(m/60); if(h<24) return h+'小时前'; return Math.floor(h/24)+'天前' }
function iconColor(ext: string) { const m: Record<string,string>={pdf:'#ef4444',doc:'#3b82f6',docx:'#3b82f6',xls:'#16a34a',xlsx:'#16a34a',jpg:'#a855f7',png:'#a855f7',zip:'#78716c',ppt:'#f97316'}; return m[ext?.toLowerCase()]||'#6b7280' }
function iconForExt(ext: string) { const m: Record<string,string>={pdf:'📕',doc:'📘',docx:'📘',xls:'📗',xlsx:'📗',ppt:'📙',pptx:'📙',jpg:'🖼',png:'🖼',zip:'📦'}; return m[ext?.toLowerCase()]||'📄' }

let overviewCache: any = null
let overviewCacheAt = 0
async function loadOverview() {
  const now = Date.now()
  if (overviewCache && now - overviewCacheAt < 30000) {
    overview.value = overviewCache
    return
  }
  try {
    overview.value = await get('/api/files/overview')
    overviewCache = overview.value
    overviewCacheAt = Date.now()
  } catch {}
}

function goOverview() {
  if (auth.isSuperAdmin) { mode.value = 'overview'; loadOverview() }
  else { mode.value = 'browse'; browseMode.value = auth.user?.department || ''; doLoad() }
}
function enterDept(dept: string) {
  mode.value = 'browse'; browseMode.value = dept; sharedView.value = false; currentFolder.value = null; viewEmployee.value = null
  page.value = 1; selected.value = []; uploaderFilter.value = ''; keyword.value = ''; doLoad(); loadFolderTree()
}
function openRecent(f: any) {
  mode.value = 'browse'; browseMode.value = f.department || ''; sharedView.value = false; currentFolder.value = null
  page.value = 1; selected.value = []; uploaderFilter.value = ''; keyword.value = ''
  if (f.parent_id) {
    currentFolder.value = f.parent_id
    selected.value = [f.id]
  }
  doLoad()
}
function enterMy() {
  prevBrowseMode.value = browseMode.value !== 'my' ? browseMode.value : prevBrowseMode.value
  mode.value = 'browse'; browseMode.value = 'my'; sharedView.value = false; currentFolder.value = null; viewEmployee.value = null
  page.value = 1; selected.value = []; uploaderFilter.value = ''; keyword.value = ''; doLoad(); loadFolderTree()
}
function enterShared() {
  mode.value = 'browse'; browseMode.value = ''; sharedView.value = true; currentFolder.value = null; viewEmployee.value = null
  page.value = 1; selected.value = []; uploaderFilter.value = ''; keyword.value = ''; doLoad()
}
function enterEmployeePrivate(u: any) {
  mode.value = 'browse'; sharedView.value = false; viewEmployee.value = {id: u.user_id, name: u.name}
  currentFolder.value = null; uploaderFilter.value = ''; keyword.value = ''; page.value = 1
  doLoad(); loadFolderTree()
}
function goAllFiles() {
  mode.value = 'browse'; sharedView.value = false; currentFolder.value = null; viewEmployee.value = null
  uploaderFilter.value = ''; keyword.value = ''; page.value = 1; doLoad(); loadFolderTree()
}
function goFolder(id: string) {
  mode.value = 'browse'; sharedView.value = false; currentFolder.value = id; viewEmployee.value = null
  uploaderFilter.value = ''; page.value = 1; doLoad()
}
function toggleUploader(id: string) {
  mode.value = 'browse'
  uploaderFilter.value = uploaderFilter.value === id ? '' : id
  page.value = 1; doLoad()
}
function goTrash() {
  mode.value = 'trash'; sharedView.value = false; currentFolder.value = null; viewEmployee.value = null
  uploaderFilter.value = ''; keyword.value = ''; page.value = 1; doLoad()
}
function goBrowse() {
  mode.value = 'browse'; page.value = 1; doLoad()
}
function backToDrive() {
  if (auth.user?.role === 'super_admin') { goOverview() }
  else { enterDept(auth.user?.department || '') }
}

function initView() {
  const q = route.query
  // Reset view mode
  view.value = defaultView()
  page.value = 1; selected.value = []; uploaderFilter.value = ''; keyword.value = ''; viewEmployee.value = null; sharedView.value = false
  if (q.dept) {
    mode.value = 'browse'; browseMode.value = q.dept as string
    currentFolder.value = null
  } else if (q.folder) {
    mode.value = 'browse'; browseMode.value = auth.user?.department || ''
    currentFolder.value = q.folder as string
  } else if (q.my) {
    mode.value = 'browse'; browseMode.value = 'my'
    currentFolder.value = null
  } else if (q.trash) {
    mode.value = 'trash'; browseMode.value = ''
    currentFolder.value = null
  } else {
    // super_admin → overview; others → their department directly
    if (auth.user?.role === 'super_admin') {
      mode.value = 'overview'
    } else {
      mode.value = 'browse'; browseMode.value = auth.user?.department || ''
    }
  }
}

async function doLoad() {
  if (mode.value === 'stars') {
    try {
      const r: any = await get('/api/files/stars')
      files.value = (r as any).items || []
      total.value = files.value.length
      breadcrumb.value = [{ id: null, name: '星标文件' }]
      selected.value = []
    } catch {
      files.value = []
    }
    return
  }
  if (mode.value === 'browse' || mode.value === 'trash') {
    loading.value = true
    try {
      const p: any = { page: page.value, size: size.value, sort: sortBy.value }
      p.in_trash = mode.value === 'trash'
      if (keyword.value) p.keyword = keyword.value
      if (fileTypeFilter.value) p.file_type = fileTypeFilter.value
      if (sharedView.value) {
        p.shared = '1'
      } else if (viewEmployee.value) {
        // 部门主管查看某员工私盘
        p.user_id = viewEmployee.value.id
        p.scope = 'private'
        p.department = browseMode.value
        if (currentFolder.value) p.parent_id = currentFolder.value
      } else if (uploaderFilter.value) {
        p.user_id = uploaderFilter.value
      }
      if (browseMode.value === 'my') {
        p.my = '1'
        if (currentFolder.value) p.parent_id = currentFolder.value
      } else if (!viewEmployee.value && currentFolder.value && !keyword.value && !uploaderFilter.value) {
        p.parent_id = currentFolder.value
        p.scope = 'dept'
      } else if (!viewEmployee.value && browseMode.value && mode.value === 'browse' && (keyword.value || uploaderFilter.value)) {
        // 搜索/员工筛选：跨全部层级，按整个部门范围查询
        p.department = browseMode.value
        p.scope = 'dept'
      } else if (!viewEmployee.value && browseMode.value && mode.value === 'browse') {
        // 部门根视图：显示全部根级文件夹（部门可能有多个根目录）
        p.department = browseMode.value
        p.scope = 'dept'
        p.root = '1'
      }
      const r: any = await get('/api/files', p)
      files.value = r.items||[]; total.value = r.total||0; breadcrumb.value = r.breadcrumb||[]
      // Force view to list if no view mode set
      if (!view.value || (view.value !== 'grid' && view.value !== 'list')) view.value = defaultView()
      // Subfolders
      try {
        const subKey = `${browseMode.value}|${currentFolder.value||''}|${viewEmployee.value?.id||''}`
        if (subKey !== lastSubKey && mode.value !== 'trash' && !sharedView.value) {
          const sq: any = {size:200,in_trash:false}
          if (viewEmployee.value) {
            sq.scope = 'private'; sq.user_id = viewEmployee.value.id; sq.department = browseMode.value
            if (currentFolder.value) sq.parent_id = currentFolder.value
          } else if (browseMode.value && browseMode.value!=='my') {
            sq.scope = 'dept'
            if (currentFolder.value) sq.parent_id = currentFolder.value
            else sq.parent_id = deptRootId.value || '__none__'
          }
          else if (browseMode.value==='my') {
            sq.my = '1'
            if (currentFolder.value) sq.parent_id = currentFolder.value
          }
          const fr: any = await get('/api/files', sq)
          allFolders.value = (fr.items||[]).filter((i:any)=>i.is_folder)
          subfolders.value = (fr.items||[]).filter((i:any)=>i.is_folder && i.parent_id===(currentFolder.value || deptRootId.value || null))
          lastSubKey = subKey
        }
      } catch {}
      // 部门成员及其私盘文件数（主管查看下属私盘入口）
      try {
        if (auth.isAdmin && browseMode.value && browseMode.value!=='my' && mode.value !== 'trash') {
          if (!deptUsersCache[browseMode.value]) {
            const ur: any = await get('/api/files/dept-users', {department: browseMode.value})
            deptUsersCache[browseMode.value] = (ur.items||[])
          }
          deptUsers.value = deptUsersCache[browseMode.value]
        }
      } catch {}
      try {
        if (!statsLoaded) {
          const st: any = await get('/api/files/stats'); statsSize.value = st.total_size||0
          statsLoaded = true
        }
      } catch {}
      // sidebar dept list
      const visibleDepts = auth.isSuperAdmin ? DEPT_NAMES : [auth.user?.department||'']
      deptList.value = visibleDepts.filter(d=>d).map(d=>({name:d,color:DEPT_CONFIG[d]?.color||'#999'}))
    } catch { files.value = []; ElMessage.error('加载失败，请稍后重试') }
    finally { loading.value = false }
  }
}

async function computeTargetParent(): Promise<string|null> {
  if (browseMode.value === 'my') return null
  if (currentFolder.value) return currentFolder.value
  if (browseMode.value) return deptRootId.value || null
  return null
}

function uploadScope(): string {
  if (browseMode.value === 'my' || viewEmployee.value) return 'private'
  return uploadScopeSel.value === 'admin' ? 'dept' : uploadScopeSel.value
}

function onTreeClick(data: any) {
  currentFolder.value = data.id
  page.value = 1
  doLoad()
}

function onDeptCheck(_data: any, info: any) {
  uploadDepts.value = ((info && info.checkedKeys) || []).filter((k: any) => k !== '__all__' && typeof k === 'string')
}

function onUsersCheck(_data: any, info: any) {
  uploadUserIds.value = ((info && info.checkedKeys) || [])
    .filter((k: any) => typeof k === 'string' && k.startsWith('u_'))
    .map((k: any) => k.slice(2))
}

async function loadUsersTree() {
  try {
    const r: any = await get('/api/files/users-tree')
    usersTreeData.value = ((r as any).items || []).map((g: any) => ({
      id: 'd_' + g.department,
      name: g.department,
      children: (g.users || []).map((u: any) => ({id: 'u_' + u.user_id, name: u.name, user_id: u.user_id})),
    }))
  } catch {
    usersTreeData.value = []
  }
}

async function loadFolderTree() {
  try {
    treeLoading.value = true
    const params: any = {}
    if (browseMode.value === 'my') params.my = true
    else if (viewEmployee.value) params.user_id = viewEmployee.value.id
    else if (browseMode.value) params.department = browseMode.value
    else return
    const r: any = await get('/api/files/tree', params)
    folderTree.value = Array.isArray(r) ? r : []
  } catch {
    folderTree.value = []
  } finally {
    treeLoading.value = false
  }
}

async function refreshAfterUpload() {
  // 总览视图（部门卡片/统计）与列表视图走不同的数据源；上传后必须刷新当前模式并清掉总览缓存
  if (mode.value === 'overview') {
    overviewCache = null
    await loadOverview()
  } else {
    await doLoad()
  }
  loadFolderTree()
}

async function processUpload(fileList: FileList | { files: { file: File; rel: string }[]; dirs: { dir: boolean; rel: string }[] } | { file: File; rel: string }[], targetParent: string|null, scope: string, allowDownload: boolean = true) {
    const token = sessionStorage.getItem('token')||localStorage.getItem('token')
    const folderMap: Record<string,string> = {}
    const failedNames: string[] = []
    let okTotal = 0
  async function uploadOne(fd: FormData, filename: string) {
    try {
      return await upload('/api/files/upload', fd)
    } catch(e:any){
      const detail = e?.response?.data?.detail
      if (detail && detail.exists) {
        const replace = await ElMessageBox.confirm(
          `「${filename}」已存在同名文件，是否覆盖？`,
          '同名文件',
          { confirmButtonText: '覆盖', cancelButtonText: '保留两份', type: 'warning' }
        ).then(()=>true).catch(()=>false)
        if (replace) {
          fd.append('overwrite', 'true')
          return await upload('/api/files/upload', fd)
        }
        return null
      }
      throw e
    }
  }
  async function ensureFolder(fp: string): Promise<string|null> {
    if(!fp||fp==='.') return targetParent
    if(folderMap[fp]) return folderMap[fp]
    const parts = fp.split('/'); let pid = targetParent
    for(const name of parts){
      if(!name) continue
      const key = pid?`${pid}/${name}`:name
      if(folderMap[key]){ pid=folderMap[key]; continue }
      try {
        const body:any = {name, parent_id: pid}
        if (browseMode.value && browseMode.value!=='my') body.department = browseMode.value
        body.scope = scope
        const resp = await fetch('/api/files/folders',{method:'POST',headers:{'Content-Type':'application/json','Authorization':`Bearer ${token}`},body:JSON.stringify(body)})
        if (!resp.ok) throw new Error(`创建文件夹「${name}」失败(${resp.status})`)
        const d=await resp.json()
        if (!d || !d.id) throw new Error(`创建文件夹「${name}」失败`)
        folderMap[key]=d.id; folderMap[fp]=d.id; pid=d.id
      } catch { return null }
    }
    if (pid) folderMap[fp]=pid
    return pid
  }
  const raw = Array.from(
    (fileList as any)?.files ? [...(fileList as any).files, ...((fileList as any).dirs || [])] : (fileList as any)
  )
  const files = raw.map((x: any) => (x instanceof File ? { file: x, rel: (x as any).webkitRelativePath || '' } : x))
  const folderDirs = files.filter((f: any) => f.dir)
  const folderFiles = files.filter((f: any) => f.rel && f.rel.includes('/'))
  const looseFiles = files.filter((f: any) => !f.dir && (!f.rel || !f.rel.includes('/')))
  // Folder upload: show single progress for entire folder
  if (folderDirs.length || folderFiles.length) {
    // 按根文件夹分组：一次拖入多个文件夹（含空文件夹）时各自独立处理
    const groups = new Map<string, { dirs: any[]; files: any[] }>()
    for (const it of [...folderDirs, ...folderFiles]) {
      const root = it.rel.split('/')[0] || '文件夹'
      if (!groups.has(root)) groups.set(root, { dirs: [], files: [] })
      const g = groups.get(root)!
      if (it.dir) g.dirs.push(it)
      else g.files.push(it)
    }
    for (const [rootName, g] of groups) {
      const totalWork = g.dirs.length + g.files.length
      const idx = uploading.value.length; uploading.value.push({name:'📁 '+rootName, pct:0, err:false, total: totalWork, done:0})
      let ok=0
      let failCount=0
      // 先创建目录（含空目录），保证空文件夹也能拖拽上传
      for(const d of g.dirs){
        try {
          const pid = await ensureFolder(d.rel)
          if (!pid) throw new Error('创建文件夹失败')
            ok++; uploading.value[idx].pct=Math.round(ok/totalWork*100); uploading.value[idx].done=ok
            okTotal++
          } catch(e:any){
            uploading.value[idx].err=true
            failCount++
            failedNames.push(d.rel)
            ElMessage.error(`「${d.rel}」创建失败：${(e as any)?.message || ''}`)
        }
      }
      for(const { file, rel } of g.files){
        // Path relative to root folder: "myFolder/sub/file.txt" → "sub"
        const rp = rel || ''
        const innerPath = rp.split('/').slice(1, -1).join('/')  // everything between root and filename
        try {
          const pid = innerPath ? (await ensureFolder(rootName+'/'+innerPath)) : (await ensureFolder(rootName))
          if (!pid) throw new Error('创建子文件夹失败')
          const fd=new FormData()
          // Strip path prefix from filename - keep only the base name
            const cleanName = file.name.split('/').pop() || file.name
            fd.append('file', file, cleanName)
            fd.append('scope', scope)
              fd.append('employee_download', allowDownload ? 'true' : 'false')
              if (scope === 'specific' && uploadDepts.value.length) fd.append('visible_departments', JSON.stringify(uploadDepts.value))
              if (uploadScopeSel.value === 'admin') fd.append('admin_only', 'true')
              if (scope === 'users' && uploadUserIds.value.length) fd.append('visible_user_ids', JSON.stringify(uploadUserIds.value))
              if(pid)fd.append('parent_id',pid); await uploadOne(fd, cleanName)
            ok++; uploading.value[idx].pct=Math.round(ok/totalWork*100); uploading.value[idx].done=ok
            okTotal++
          } catch(e:any){
            uploading.value[idx].err=true
            failCount++
            failedNames.push(rel || file.name)
            ElMessage.error(`「${file.name}」上传失败：${(e as any)?.message || ''}`)
        }
      }
      if (ok>0) { ElMessage.success(failCount ? `📁 ${rootName} 上传完成 (${ok}/${totalWork}，${failCount} 个失败)` : `📁 ${rootName} 上传完成 (${ok}/${totalWork})`) }
    }
  }
    if (looseFiles.length) {
      // Single/multi file upload: show individual progress
      const names: string[] = []
      let looseOk = 0
      for(const { file } of looseFiles){
        const idx=uploading.value.length; uploading.value.push({name:file.name, pct:0, err:false})
        try {
          const fd=new FormData(); fd.append('file',file); fd.append('scope', scope); fd.append('employee_download', allowDownload ? 'true' : 'false')
          if (scope === 'specific' && uploadDepts.value.length) fd.append('visible_departments', JSON.stringify(uploadDepts.value))
          if (uploadScopeSel.value === 'admin') fd.append('admin_only', 'true')
          if (scope === 'users' && uploadUserIds.value.length) fd.append('visible_user_ids', JSON.stringify(uploadUserIds.value))
          if(targetParent)fd.append('parent_id',targetParent)
          await uploadOne(fd, file.name); uploading.value[idx].pct=100; names.push(file.name); looseOk++
        } catch(e:any){ uploading.value[idx].err=true; failedNames.push(file.name); ElMessage.error(`${file.name} 失败`) }
      }
      if(names.length){ ElMessage.success(`已上传 ${names.length} 个文件`) }
      okTotal += looseOk
    }
    uploading.value=[]
    return { ok: okTotal, fail: failedNames }
  }

async function onUpload(e: Event) {
    const input = e.target as HTMLInputElement
    const fl = input.files; if(!fl?.length) return
  // 目录选择框必须有 webkitRelativePath，否则无法保留目录结构，直接报错而不是平铺上传
  const isDirInput = !!(input as any).webkitdirectory
  const isFolder = !!(Array.from(fl)[0] as any).webkitRelativePath
  if (isDirInput && !isFolder) {
    ElMessage.error('当前浏览器未提供文件夹结构信息，无法保留目录。请使用 Chrome/Edge 浏览器或直接拖拽文件夹上传')
      input.value=''
      return
    }
    const newItems = Array.from(fl).map((f: File) => ({
      file: f,
      rel: (f as any).webkitRelativePath || f.name,
    }))
    const existing = new Set(pendingFiles.value.map(p => p.rel))
    pendingFiles.value = [...pendingFiles.value, ...newItems.filter((i: any) => !existing.has(i.rel))]
    pendingDirs.value = []
    pendingDirCount.value = (pendingDirCount.value || 0) + (isDirInput ? 1 : 0)
    uploadOpen.value = true
    input.value=''
  }

function onClick(f:any,e:MouseEvent){
  if(e.ctrlKey||e.metaKey){
    const i=selected.value.indexOf(f.id); i>=0?selected.value.splice(i,1):selected.value.push(f.id)
  } else if (f.is_folder) {
    // 单击文件夹直接打开（Ctrl+点击可多选）
    openItem(f)
  } else {
    selected.value=[f.id]
  }
}
function openItem(f:any){ if(f.is_folder){ currentFolder.value=f.id; keyword.value=''; uploaderFilter.value=''; selected.value=[]; page.value=1; doLoad() } else { openPreview(f) } }
function goBackFolder(){
    if (sharedView.value) {
      currentFolder.value = null; doLoad()
    } else if (breadcrumb.value.length > 2) {
    var prev = breadcrumb.value[breadcrumb.value.length - 2]
    currentFolder.value = prev.id; doLoad()
  } else if (currentFolder.value) {
    currentFolder.value = null; doLoad()
  } else if (viewEmployee.value) {
    viewEmployee.value = null; currentFolder.value = null; doLoad()
  } else if (browseMode.value === 'my') {
    // 从“我的文件”返回：优先回到进入前的部门盘，否则回公盘入口
    if (prevBrowseMode.value) { enterDept(prevBrowseMode.value); prevBrowseMode.value = '' }
    else { backToDrive() }
  } else if (auth.isSuperAdmin) {
    goOverview()
  } else {
    // 普通员工在部门盘根目录没有更上层，返回首页
    router.push('/')
  }
}
function toggleAll(){ if(allSelected.value) selected.value=[]; else selected.value=files.value.map((f:any)=>f.id) }
function toggleOne(id:string){ const i=selected.value.indexOf(id); i>=0?selected.value.splice(i,1):selected.value.push(id) }

const renameTarget=ref<any>(null); const renameName=ref(''); const renameVisible=ref(false)
const renameEmpDownload=ref(true)
function startRename(f:any){ renameTarget.value=f; renameName.value=f.filename; renameEmpDownload.value = f.employee_download !== false; renameVisible.value=true }
async function doRename(){
  if(!renameName.value.trim()||renameName.value===renameTarget.value?.filename){ renameVisible.value=false; return }
  try{ await put(`/api/files/${renameTarget.value.id}`,{name:renameName.value, employee_download: renameTarget.value.is_folder ? undefined : renameEmpDownload.value}); renameVisible.value=false; doLoad() }
  catch { ElMessage.error('重命名失败') }
}
function canDownload(f:any){
  if(auth.isAdmin) return true
  if(f.user_id && auth.user && f.user_id===auth.user.id) return true
  return f.employee_download !== false
}

async function doDownload(f:any){
  try{
    const resp:any = await get(`/api/files/${f.id}/download-token`)
    window.location.href = `/api/files/${f.id}/download?token=${encodeURIComponent(resp.token)}`
  } catch { ElMessage.error('下载失败') }
}
async function batchDownload(){
  if(!selected.value.length) return
  const ids = selected.value.filter((id: string) => {
    const f = files.value.find((x: any) => x.id === id)
    return f && canDownload(f)
  })
  if(!ids.length){ ElMessage.warning('没有可下载的文件（未开放员工下载）'); return }
  if(ids.length < selected.value.length) ElMessage.warning(`已跳过 ${selected.value.length - ids.length} 个未开放下载的文件`)
  try{
    const token = sessionStorage.getItem('token')||localStorage.getItem('token')
    const resp = await fetch('/api/files/batch/download',{
      method:'POST',
      headers:{'Content-Type':'application/json','Authorization':`Bearer ${token}`},
      body:JSON.stringify({ids})
    })
    if(!resp.ok){
      const d = await resp.json().catch(()=>null)
      throw new Error(d?.detail || '下载失败')
    }
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '批量下载.zip'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch(e:any){
    ElMessage.error(e?.message || '下载失败')
  }
}
const share = reactive({ open: false, url: '', days: 7, fileId: '' })
async function shareFile(f: any) {
  share.fileId = f.id
  share.days = 7
  share.url = ''
  share.open = true
  try {
    const resp: any = await post(`/api/files/${f.id}/share`, { expire_days: 7 })
    share.url = window.location.origin + resp.url
  } catch {
    ElMessage.error('生成分享链接失败')
  }
}
async function refreshShareUrl() {
  if (!share.fileId) return
  try {
    const resp: any = await post(`/api/files/${share.fileId}/share`, { expire_days: share.days })
    share.url = window.location.origin + resp.url
  } catch {
    ElMessage.error('生成分享链接失败')
  }
}
async function copyShare() {
  try {
    await navigator.clipboard.writeText(share.url)
    ElMessage.success('链接已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}
async function doTrash(f:any){
  try{
    await ElMessageBox.confirm(`确定删除"${f.filename}"？`,'移到回收站',{type:'warning'})
    await del(`/api/files/${f.id}`)
    ElMessage.success('已移入回收站')
    doLoad()
  } catch(e:any){
    if(e !== 'cancel' && e !== 'close') ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}
async function batchTrash(){
  if(!selected.value.length) return
  try{
    await ElMessageBox.confirm(`删除${selected.value.length}项？`,'批量删除',{type:'warning'})
    await post('/api/files/batch/trash',{ids:selected.value})
    selected.value=[]
    ElMessage.success('已移入回收站')
    doLoad()
  } catch(e:any){
    if(e !== 'cancel' && e !== 'close') ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}
async function batchRestore(){ await post('/api/files/batch/restore',{ids:selected.value}); selected.value=[]; doLoad() }
async function batchDeletePermanent(){ try{ await ElMessageBox.confirm('永久删除不可恢复！','⚠️',{type:'error'} as any); await del('/api/files/batch/permanent',{ids:selected.value}); selected.value=[]; doLoad() } catch {} }
async function doMove(tid:string|null){
  try{
    await post('/api/files/batch/move',{ids:selected.value,target_folder_id:tid})
    moveVisible.value=false
    doLoad()
  } catch(e:any){
    ElMessage.error(e?.response?.data?.detail || '移动失败')
  }
}
async function emptyTrash(){
  try { await ElMessageBox.confirm('永久删除回收站所有文件？','⚠️',{type:'error'} as any) } catch { return }
  try {
    await del('/api/files/batch/empty-trash')
    ElMessage.success('回收站已清空')
    await doLoad()
  } catch(e:any) {
    ElMessage.error(e?.response?.data?.detail || '清空回收站失败，请稍后重试')
  }
}

function showNewFolder(){ newFolderName.value=''; newFolderVisible.value=true }
async function createFolder(){ if(!newFolderName.value.trim()) return; try{
  const body:any = {name:newFolderName.value.trim(), parent_id:currentFolder.value||null, scope: uploadScope()}
  if (browseMode.value && browseMode.value!=='my') {
    body.department = browseMode.value
    if (!currentFolder.value && !viewEmployee.value) {
      const info = overview.value.dept_stats?.find((d:any)=>d.department===browseMode.value)
      if (info?.folder_id) body.parent_id = info.folder_id
    }
  }
  await post('/api/files/folders',body); newFolderVisible.value=false; newFolderName.value=''; doLoad(); ElMessage.success('文件夹已创建')
} catch { ElMessage.error('创建失败') } }

const previewFile=ref<any>(null); const previewShow=ref(false); const previewUrl=ref('')
let previewBusy=false
let previewLastId=''
let previewLastAt=0
const isOffice=(ext:string)=>['doc','docx','xls','xlsx','ppt','pptx','pdf','odt','ods','odp','txt','csv','md'].includes(ext?.toLowerCase())
const isImage=(ext:string)=>['jpg','jpeg','png','gif','bmp','webp','svg'].includes(ext?.toLowerCase())
const isVideo=(ext:string)=>['mp4','webm','ogg','ogv','m4v','mov'].includes(ext?.toLowerCase())
const isAudio=(ext:string)=>['mp3','wav','m4a','aac','flac','ogg'].includes(ext?.toLowerCase())
const imageFiles = computed(()=>files.value.filter(f=>!f.is_folder && isImage(f.file_ext)))
const previewIdx = computed(()=>{ const i=imageFiles.value.findIndex(f=>f.id===previewFile.value?.id); return i<0?0:i })
const hasPrev = computed(()=>previewIdx.value>0)
const hasNext = computed(()=>previewIdx.value<imageFiles.value.length-1)
function previewStep(delta:number){
  const list=imageFiles.value; if(!list.length) return
  const next=(previewIdx.value+delta+list.length)%list.length
  previewUrl.value=''
  previewFile.value=list[next]
}
function onPreviewKey(e:KeyboardEvent){
  if(!previewShow.value || previewBusy) return
  if(e.key==='ArrowLeft'){ e.preventDefault(); previewStep(-1) }
  else if(e.key==='ArrowRight'){ e.preventDefault(); previewStep(1) }
}
function openPreview(f:any){
  if(!f||f.is_folder) return
  if(previewBusy){ ElMessage.info('正在加载预览，请稍候'); return }
  const now=Date.now()
  if(previewLastId===f.id && now-previewLastAt<3000) return
  previewLastId=f.id; previewLastAt=now
  previewFile.value=f
}
watch(previewFile,async(f)=>{
  if(!f||f.is_folder) return
  if(previewBusy){ previewFile.value=null; return }
  previewBusy=true
  previewUrl.value=''
  const token=sessionStorage.getItem('token')||localStorage.getItem('token')
  const ext=f.file_ext?.toLowerCase()
  const loading=ElLoading.service({ fullscreen:true, lock:true, text:'正在加载预览，请稍候…' })
  try {
    if(isOffice(ext)){
      previewShow.value=false; previewFile.value=null
      window.open(`/files/preview/${f.id}?from=${encodeURIComponent(currentFolder.value || '')}&ext=${f.file_ext || ''}`,'_blank')
      // 新标签页打开后稍作停留，让用户看到加载反馈而不是闪一下就消失
      await new Promise((r)=>setTimeout(r, 900))
    } else if(isImage(ext) || isVideo(ext) || isAudio(ext)){
      previewShow.value=true
      try{
        const resp=await fetch(`/api/files/${f.id}/preview`,{headers:{Authorization:`Bearer ${token}`}})
        const d=await resp.json()
        previewUrl.value=d.preview_url||''
      } catch { ElMessage.error('预览失败') }
    } else {
      previewShow.value=false; ElMessage.info('该格式暂不支持预览，已开始下载'); doDownload(f); previewFile.value=null
    }
  } finally {
    loading.close(); previewBusy=false
  }
})

async function onDrop(e: DragEvent) {
    dragDepth = 0
    dragOver.value=false
    if(dragItem.value){ await doMoveTo(currentFolder.value); dragItem.value=null; return }
    // 仅系统文件拖入才进入上传流程（内部 HTML 拖拽不携带 Files）
    const hasFiles = !!e.dataTransfer && Array.from(e.dataTransfer.types || []).includes('Files')
    if (!hasFiles) return
    const list = await collectDropFiles(e)
    if (!list.files.length && !list.dirs.length) { ElMessage.warning('未识别到拖入的文件，请直接拖入文件或文件夹'); return }
    const existingFiles = new Set(pendingFiles.value.map(p => p.rel))
    const existingDirs = new Set(pendingDirs.value.map(d => d.rel))
    pendingFiles.value = [
      ...pendingFiles.value,
      ...list.files.filter((f: any) => !existingFiles.has(f.rel)),
    ]
    pendingDirs.value = [
      ...pendingDirs.value,
      ...list.dirs.filter((d: any) => !existingDirs.has(d.rel)),
    ]
    pendingDirCount.value = pendingDirs.value.length
    uploadOpen.value = true
  }

  function openUploadDialog(kind: 'file' | 'folder') {
    if (kind === 'folder') (fDirInp.value as any)?.click()
    else (fInp.value as any)?.click()
  }

  function pickFiles() {
    (fInp.value as any)?.click()
  }

  function pickFolder() {
    (fDirInp.value as any)?.click()
  }

  async function startUpload() {
    if (!pendingFiles.value.length) return
    const files = pendingFiles.value
    const dirs = pendingDirs.value
    // 本地清单（相对路径 + 大小），上传完成后自动对比服务器
    const manifest = files.map((p: any) => ({ name: p.rel || p.file.name, size: p.file.size || 0 }))
    uploadOpen.value = false
    const targetParent = await computeTargetParent()
    const res = await processUpload({ files, dirs } as any, targetParent, uploadScope(), allowEmpDownload.value)
    pendingFiles.value = []
    pendingDirs.value = []
    pendingDirCount.value = 0
    uploadResult.value = { open: true, ok: res?.ok || 0, fail: res?.fail || [], integrity: undefined }
    await refreshAfterUpload()
    loadFolderTree()
    // 上传完整性自动对比：少了 N / 多了 N / 全部完整
    try {
      const v: any = await post('/api/files/verify', { parent_id: targetParent || null, expected: manifest })
      uploadResult.value.integrity = v
    } catch {
      uploadResult.value.integrity = undefined
    }
  }

  function toggleTree() {
    treeMode.value = !treeMode.value
    if (treeMode.value) loadFolderTree()
  }

  async function exportManifest() {
    const folderId = currentFolder.value || deptRootId.value
    if (!folderId) { ElMessage.warning('请先进入要导出的文件夹'); return }
    try {
      const r: any = await get('/api/files/manifest', { folder_id: folderId })
      const rows = r.files || []
      const esc = (s: string) => '"' + String(s || '').replace(/"/g, '""') + '"'
      const lines = ['"相对路径","大小(字节)","修改时间"']
      for (const f of rows) lines.push(`${esc(f.path)},${f.size},${esc(f.updated_at || '')}`)
      const csv = '\ufeff' + lines.join('\r\n')
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `${r.folder || '清单'}_文件清单.csv`
      a.click()
      URL.revokeObjectURL(a.href)
      ElMessage.success(`已导出 ${rows.length} 个文件（${formatSize(r.total_size || 0)}）`)
    } catch {
      ElMessage.error('导出清单失败')
    }
  }

  const sendTreeData = computed(() => {
    const kw = sendKeyword.value.trim()
    if (!kw) return usersTreeData.value
    return usersTreeData.value
      .map((g: any) => ({...g, children: (g.children || []).filter((u: any) => u.name.includes(kw))}))
      .filter((g: any) => g.children.length)
  })

  function openSendDialog(f: any) {
    sendTargets.value = [f]
    sendToUser.value = null
    sendMessage.value = ''
    sendKeyword.value = ''
    sendOpen.value = true
    loadUsersTree()
  }

  function openSendMulti() {
    const sel = files.value.filter((f: any) => selected.value.includes(f.id))
    if (!sel.length) return
    sendTargets.value = sel
    sendToUser.value = null
    sendMessage.value = ''
    sendKeyword.value = ''
    sendOpen.value = true
    loadUsersTree()
  }

  function onSendUserClick(data: any) {
    if (data.user_id) sendToUser.value = data
  }

  async function doSendFile() {
    if (!sendTargets.value.length || !sendToUser.value) return
    try {
      const r: any = await post('/api/files/transfers/send', {
        file_ids: sendTargets.value.map((t: any) => t.id),
        to_user_id: sendToUser.value.user_id,
        message: sendMessage.value,
      })
      ElMessage.success(`已发送 ${r.count || sendTargets.value.length} 个文件给 ${sendToUser.value.name}`)
      sendOpen.value = false
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || '发送失败')
    }
  }

  async function openSent() {
    sentOpen.value = true
    await loadSent()
  }

  async function loadSent() {
    try {
      const r: any = await get('/api/files/transfers/sent')
      sentList.value = (r as any).items || []
    } catch {
      sentList.value = []
    }
  }

  async function doRevoke(t: any) {
    try {
      await post(`/api/files/transfers/${t.id}/revoke`)
      ElMessage.success('已撤回')
      await loadSent()
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || '撤回失败')
    }
  }

  async function openTransfers() {
    transfersOpen.value = true
    await loadIncoming()
  }

  async function loadIncoming() {
    try {
      const r: any = await get('/api/files/transfers/incoming')
      const items = (r as any).items || []
      incoming.value = items
      incomingCount.value = items.length
      if (lastIncomingCount >= 0) {
        const fresh = items.filter((t: any) => !seenTransferIds.has(t.id))
        if (fresh.length) notifyIncoming(fresh)
      }
      for (const t of items) seenTransferIds.add(t.id)
      lastIncomingCount = items.length
    } catch {
      incoming.value = []
      incomingCount.value = 0
    }
  }

  function notifyIncoming(items: any[]) {
    const names = items.slice(0, 3).map((t: any) => t.filename).join('、')
    try {
      const Ctx: any = (window as any).AudioContext || (window as any).webkitAudioContext
      if (Ctx) {
        const ctx = new Ctx()
        const osc = ctx.createOscillator()
        const gain = ctx.createGain()
        osc.connect(gain)
        gain.connect(ctx.destination)
        osc.frequency.value = 880
        gain.gain.value = 0.12
        osc.start()
        osc.stop(ctx.currentTime + 0.25)
        setTimeout(() => { try { ctx.close() } catch {} }, 600)
      }
    } catch {}
    try {
      if ('Notification' in window) {
        const body = `来自 ${items[0]?.from_name || ''}：${names}`
        if (Notification.permission === 'granted') {
          new Notification('收到新的文件传输', { body, tag: 'kb_user-transfer' })
        } else if (Notification.permission !== 'denied') {
          Notification.requestPermission().then((p: any) => {
            if (p === 'granted') new Notification('收到新的文件传输', { body, tag: 'kb_user-transfer' })
          })
        }
      }
    } catch {}
    ElMessage.info(`收到新的文件传输：${names}`)
  }

  async function goStars() {
    mode.value = 'stars'
    sharedView.value = false
    currentFolder.value = null
    viewEmployee.value = null
    page.value = 1
    selected.value = []
    keyword.value = ''
    uploaderFilter.value = ''
    await doLoad()
  }

  async function toggleStar(f: any) {
    try {
      if (f.starred) {
        await del(`/api/files/${f.id}/star`)
        f.starred = false
        ElMessage.success('已取消星标')
      } else {
        await post(`/api/files/${f.id}/star`)
        f.starred = true
        ElMessage.success('已星标收藏')
      }
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || '操作失败')
    }
  }

  function onRowCmd(cmd: string, f: any) {
    if (cmd === 'share') shareFile(f)
    else if (cmd === 'preview') openPreview(f)
    else if (cmd === 'rename') startRename(f)
  }

  function onTypeFilter() {
    page.value = 1
    doLoad()
  }

  async function doAccept(t: any) {
    try {
      await post(`/api/files/transfers/${t.id}/accept`)
      ElMessage.success(`已接收「${t.filename}」到我的私盘`)
      await loadIncoming()
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || '接收失败')
    }
  }

  async function doReject(t: any) {
    try {
      await post(`/api/files/transfers/${t.id}/reject`)
      ElMessage.info('已拒绝')
      await loadIncoming()
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || '操作失败')
    }
  }

function walkEntry(
  entry: any,
  path: string,
  files: { file: File; rel: string }[],
  dirs: { dir: boolean; rel: string }[],
): Promise<void> {
  return new Promise((resolve) => {
    if (!entry) { resolve(); return }
    if (entry.isFile) {
      entry.file((f: File) => {
        files.push({ file: f, rel: path ? `${path}/${f.name}` : f.name })
        resolve()
      }, resolve)
      return
    }
    if (entry.isDirectory) {
      const dirPath = path ? `${path}/${entry.name}` : entry.name
      dirs.push({ dir: true, rel: dirPath })
      const reader = entry.createReader()
      const readAll = () => {
        reader.readEntries(async (entries: any[]) => {
          if (!entries.length) { resolve(); return }
          for (const en of entries) {
            await walkEntry(en, dirPath, files, dirs)
          }
          readAll()
        }, resolve)
      }
      readAll()
      return
    }
    resolve()
  })
}

async function collectDropFiles(e: DragEvent): Promise<{ files: { file: File; rel: string }[]; dirs: { dir: boolean; rel: string }[] }> {
  const files: { file: File; rel: string }[] = []
  const dirs: { dir: boolean; rel: string }[] = []
  // 事件一开始就同步捕获，拖拽会话结束后 DataTransfer 会被清空/失效
  const items = Array.from(e.dataTransfer?.items || [])
  const fl = e.dataTransfer?.files ? Array.from(e.dataTransfer.files) : []
  let entryFound = false
  for (const it of items) {
    const entry: any = it.webkitGetAsEntry?.()
    if (!entry) continue
    entryFound = true
    await Promise.race([
      walkEntry(entry, '', files, dirs),
      new Promise((res) => setTimeout(res, 8000)),
    ])
  }
  if (fl.length) {
    for (const f of Array.from(fl)) {
      const rel = (f as any).webkitRelativePath || f.name
      // 真实拖拽文件夹时 files 里只有 0 字节占位 File，跳过（内容已由目录遍历收集）
      if (entryFound && f.size === 0 && !(f as any).webkitRelativePath) continue
      // 兜底路径下也跳过 0 字节、无扩展名的文件夹占位
      if (!entryFound && f.size === 0 && !(f as any).webkitRelativePath && !f.name.includes('.')) {
        dirs.push({ dir: true, rel: f.name })
        continue
      }
      if (files.some((c) => c.rel === rel && c.file.size === f.size)) continue
      files.push({ file: f, rel })
    }
  }
  return { files, dirs }
}
async function doMoveTo(tid: string|null) { if(!dragItem.value) return; try { await post('/api/files/batch/move',{ids:[dragItem.value.id],target_folder_id:tid}); doLoad() } catch { ElMessage.error('移动失败') } }
function onSearch(){ if(_t)clearTimeout(_t); _t=setTimeout(()=>{page.value=1;doLoad()},300) }
function onPageChange(){ selected.value=[]; doLoad() }
let overviewLoaded = false
onMounted(async ()=>{
  window.addEventListener('keydown', onPreviewKey)
  if (!auth.user) { try { await auth.fetchMe() } catch {} }
  await loadOverview()
  overviewLoaded = true
  initView()
  await doLoad()
  loadFolderTree()
  loadUsersTree()
  loadIncoming()
  incomingTimer = setInterval(() => { loadIncoming() }, 20000)
})
onBeforeUnmount(()=>{
  window.removeEventListener('keydown', onPreviewKey)
  if (incomingTimer) clearInterval(incomingTimer)
})
watch(()=>route.query, ()=>{ initView(); if(overviewLoaded) doLoad() })
</script>

<style scoped>
.drive-page { height:calc(100vh - 56px); max-width:1400px; margin:0 auto; padding:16px 20px; display:flex; }

/* ===== OVERVIEW ===== */
.overview { flex:1; overflow-y:auto; }
.ov-title { font-size:18px; font-weight:700; margin:0 0 16px; }
.dept-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:20px; }
.dept-card { background:#fff; border-radius:10px; padding:16px; border:1px solid #e5e7eb; border-top:3px solid #999; cursor:pointer; transition:box-shadow .15s ease, transform .15s ease, border-color .15s ease; will-change: transform; }
.dept-card:hover { box-shadow:0 4px 16px rgba(0,0,0,.08); transform:translateY(-2px); }
.dc-header { display:flex;align-items:center; gap:8px; margin-bottom:10px; }
.dc-dot { width:10px;height:10px;border-radius:50%; }
.dc-name { font-weight:600; font-size:13px; }
.dc-stats { display:flex; gap:16px; font-size:13px; color:#666; margin-bottom:6px; }
.dc-footer { font-size:11px; color:#999; }
.ov-section { margin-bottom:20px; }
.ov-section h3 { font-size:14px; margin:0 0 8px; }
.recent-list { display:flex;flex-direction:column; gap:2px; }
.recent-row { display:flex;align-items:center; gap:10px; padding:8px 12px; border-radius:6px; cursor:pointer; font-size:13px; transition:background-color .1s ease; }
.recent-row:hover { background:#f0f4f8; }
.recent-icon { font-size:16px; flex-shrink:0; }
.recent-name { flex:1; overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }
.recent-dept { font-size:11px; font-weight:500; }
.recent-user { font-size:11px; color:#999; }
.recent-time { font-size:11px; color:#bbb; white-space:nowrap; }
.ov-actions { display:flex; gap:12px; }
.act-btn { display:flex;align-items:center; gap:6px; padding:10px 20px; border:1px solid #d0d5dd; border-radius:8px; background:#fff; cursor:pointer; font-size:13px; transition:background-color .1s ease, border-color .1s ease; font-family:inherit; }
.act-btn:hover { background:#f0f4f8; border-color:#b0b8c4; }

/* ===== ENTRY ===== */
.entry { flex:1; display:flex;flex-direction:column;align-items:center; padding-top:60px; }
.entry-cards { display:flex; gap:24px; margin-top:24px; }
.entry-card { width:260px; padding:32px 24px; border:2px solid #e5e7eb; border-radius:16px; text-align:center; cursor:pointer; transition:border-color .15s ease, box-shadow .15s ease; }
.entry-card:hover { border-color:var(--color-primary); box-shadow:0 4px 20px rgba(30,80,174,.1); }
.ec-icon { font-size:48px; margin-bottom:12px; }
.ec-title { font-size:16px; font-weight:600; margin-bottom:6px; }
.ec-desc { font-size:13px; color:#888; margin-bottom:16px; }
.entry-trash { margin-top:24px; display:flex;align-items:center;gap:6px; font-size:13px; color:#888; cursor:pointer; }
.entry-trash:hover { color:var(--color-primary); }

/* ===== BROWSER ===== */
.drive-sidebar { width:200px; flex-shrink:0; background:#fafbfc; border-right:1px solid #e5e7eb; padding:12px 0; display:flex;flex-direction:column; overflow-y:auto; }
.side-hd { padding:0 16px 10px; font-size:12px; font-weight:700; }
.side-section-title { padding:8px 16px 4px; font-size:10px; color:#999; font-weight:600; }
.side-item { display:flex;align-items:center; gap:8px; padding:7px 16px; cursor:pointer; font-size:13px; color:#444; transition:background-color .1s ease; }
.side-item:hover { background:#eef1f5; }
.side-item.active { background:#e8f0fe; color:var(--color-primary); font-weight:500; }
.side-item.trash { color:#888; }
.dept-dot { width:8px;height:8px;border-radius:50%;flex-shrink:0; }
.side-divider { height:1px; background:#e5e7eb; margin:6px 16px; }
.side-stats { margin-top:auto; padding:12px 16px; }
.stat-label { font-size:11px; color:#999; margin-bottom:4px; }
.stat-bar { height:4px; background:#e5e7eb; border-radius:2px; overflow:hidden; }
.stat-fill { height:100%; background:var(--color-primary); border-radius:2px; transition:width .3s; }

.drive-main { flex:1; min-width:0; display:flex;flex-direction:column; overflow:hidden; padding-left:20px; }

.browse-header { display:flex;align-items:center; gap:12px; padding:8px 0 16px; }
.browse-title { display:flex;align-items:center; gap:6px; font-size:16px; min-height:24px; flex-wrap:nowrap; overflow:hidden; }
.browse-icon { font-size:20px; }
.browse-name { font-weight:700; }
.browse-bread { font-size:13px; color:#999; display:inline-flex; align-items:center; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.bc-seg { cursor:pointer; color:#666; }
.bc-seg:hover { color:var(--color-primary); }
.browse-stats { margin-left:auto; font-size:12px; color:#999; display:flex;gap:4px; }

.browse-toolbar { display:flex;align-items:center; gap:6px; padding:0 0 14px; flex-wrap:wrap; }
.tb-sep { width:1px; height:20px; background:#d0d5dd; margin:0 4px; }
.tb-right { display:flex;gap:6px; margin-left:auto; }

.drag-overlay { position:fixed; top:0;left:0;right:0;bottom:0; z-index:9999; background:rgba(30,80,174,.92); display:flex;flex-direction:column;align-items:center;justify-content:center; color:#fff; }
.drag-overlay p { margin-top:12px; font-size:18px; font-weight:600; }

.drive-toolbar { display:flex;align-items:center; gap:6px; padding:0 0 12px; flex-wrap:wrap; }
.tool-left { display:flex;gap:6px; }
.tool-right { display:flex;gap:6px; margin-left:auto; }
.btn,.btn-primary { padding:7px 14px; border-radius:6px; font-size:13px; cursor:pointer; border:1px solid #d0d5dd; background:#fff; color:#333; display:flex;align-items:center;gap:5px; transition:background-color .12s ease, border-color .12s ease, color .12s ease; font-family:inherit; }
.btn:hover { background:#f0f4f8; border-color:#b0b8c4; }
.btn.active { background:#e8f0fe; border-color:var(--color-primary); color:var(--color-primary); }
.btn.danger { color:#e74c3c; border-color:#f5c6cb; }
.btn.danger:hover { background:#fef0f0; }
.btn-primary { background:var(--color-primary); color:#fff; border-color:var(--color-primary); }
.btn-primary:hover { opacity:.9; }
.search-inp { padding:7px 10px; border:1px solid #d0d5dd; border-radius:6px; font-size:13px; width:140px; outline:none; font-family:inherit; }
.search-inp:focus { border-color:var(--color-primary); }
.up-queue { margin-bottom:8px; }
.up-row { display:flex;align-items:center; gap:12px; font-size:12px; padding:4px 0; }
.loading-tip { padding:24px 0; text-align:center; color:#999; font-size:13px; }
.drive-list { min-height: 40vh; }
.drive-grid { min-height: 40vh; }

.drive-head { display:flex;align-items:center; padding:8px 12px; border-bottom:2px solid #e5e7eb; font-size:12px; color:#888; font-weight:500; flex-shrink:0; }
.h-check { width:36px; flex-shrink:0; }
.h-name { flex:3; cursor:pointer; }
.h-size { width:80px; cursor:pointer; }
.h-type { width:70px; }
.h-date { width:120px; cursor:pointer; }
.h-uploader { width:70px; }
.h-act { min-width:150px; text-align:right; }

.drive-list { flex:1; overflow-y:auto; }
.l-row { display:flex;align-items:center; padding:10px 12px; border-bottom:1px solid #f0f0f0; cursor:pointer; font-size:13px; transition:background-color .08s ease; }
.l-row:hover { background:#f6f8fa; }
.l-row.sel { background:#e8f0fe; }
.l-act { opacity: 0; transition: opacity .12s ease; }
.l-row:hover .l-act, .l-row.sel .l-act { opacity: 1; }
@media (hover: none) {
  .l-act { opacity: 1; }
}
.l-check { width:36px; flex-shrink:0; }
.l-name { flex:3; display:flex;align-items:center; gap:8px; min-width:0; }
.l-name span { overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }
.l-size { width:130px; color:#888; font-size:11px; }
.l-type { width:70px; color:#888; font-size:12px; }
.l-date { width:120px; color:#888; font-size:12px; }
.l-uploader { width:70px; color:#888; font-size:12px; }
.l-act {
  width: auto;
  min-width: 170px;
  display: flex;
  flex-wrap: nowrap;
  justify-content: flex-end;
  align-items: center;
  gap: 2px;
}
.l-act .el-button {
  margin-left: 0 !important;
  padding: 4px 7px;
  font-size: 12px;
}
.l-act .el-button + .el-button {
  margin-left: 0 !important;
}

.drive-grid { flex:1; overflow-y:auto; display:grid; grid-template-columns:repeat(auto-fill,140px); gap:12px; align-content:start; padding:8px 0; min-height:0; }
.g-item { width:140px; padding:12px 8px; border-radius:10px; border:1px solid transparent; cursor:pointer; text-align:center; position:relative; transition:background-color .12s ease, border-color .12s ease; }
.g-item:hover { background:#f6f8fa; border-color:#d0d8e4; }
.g-item.sel { background:#e8f0fe; border-color:var(--color-primary); }
.g-check { position:absolute; top:4px; left:6px; opacity:0; transition:opacity .1s ease; }
.g-item:hover .g-check,.g-item.sel .g-check { opacity:1; }
.g-icon { margin:4px 0 6px; }
.g-name { font-size:12px; color:#333; word-break:break-all; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; line-height:1.3; }
.g-meta { font-size:11px; color:#999; margin-top:2px; text-align:center; max-width:120px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.dl-switch { display:inline-flex; align-items:center; gap:4px; margin-left:8px; font-size:12px; color:#666; cursor:pointer; user-select:none; }
.dl-lock { margin-left:4px; font-size:11px; }

.drive-empty { flex:1; display:flex;flex-direction:column;align-items:center;justify-content:center; color:#bbb; padding:40px; }
.drive-empty p { margin-top:8px; font-size:13px; }
.drive-foot { display:flex;justify-content:center; padding:12px 0 0; flex-shrink:0; }
.move-list { max-height:300px; overflow-y:auto; }
.move-item { padding:8px 12px; cursor:pointer; border-radius:6px; font-size:13px; }
.move-item:hover { background:#f0f4f8; color:var(--color-primary); }

@media (max-width:1100px) { .dept-grid { grid-template-columns:repeat(2,1fr); } }
@media (max-width:700px) { .dept-grid { grid-template-columns:1fr; }; .entry-cards { flex-direction:column; } }
.share-row { display:flex; align-items:center; gap:12px; margin-bottom:10px; }
.share-box { background:#f8fafc; border:1px dashed #cbd5e1; border-radius:8px; padding:12px; }
.share-box code { font-family:Consolas, Monaco, monospace; font-size:12px; word-break:break-all; }
.share-tip { font-size:12px; color:#94a3b8; margin:8px 0 0; }

/* 手机端基础适配 */
@media (max-width: 960px) {
  .drive-page > template, .drive-page { flex-direction: column; }
  .drive-sidebar {
    width: 100%; flex-direction: row; flex-wrap: nowrap; overflow-x: auto;
    border-right: none; border-bottom: 1px solid #e5e7eb; padding: 8px 10px; gap: 6px;
  }
  .drive-sidebar .side-section-title, .drive-sidebar .side-divider, .drive-sidebar .side-stats { display: none; }
  .drive-sidebar .side-item { flex-shrink: 0; white-space: nowrap; }
  .drive-main { padding-left: 10px; overflow-x: auto; }
  .browse-toolbar { flex-wrap: wrap; gap: 6px; }
  .browse-toolbar .tb-right { margin-left: auto; }
  .drive-head, .drive-list { min-width: 760px; }
  .browse-header { flex-wrap: wrap; }
}
@media (max-width: 600px) {
  .drive-page { padding: 8px; }
  .btn, .btn-primary { padding: 6px 10px; font-size: 12px; }
  .search-inp { width: 120px !important; }
  .drive-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    padding: 8px 0;
  }
  .g-item {
    width: 100%;
    padding: 10px 6px;
  }
  .g-icon {
    font-size: 32px;
  }
  .g-name {
    font-size: 12px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    word-break: break-all;
  }
  .drive-sidebar .side-item {
    padding: 7px 8px;
    font-size: 12px;
  }
  .browse-toolbar {
    padding-bottom: 8px;
  }
  .browse-toolbar .tb-right {
    margin-left: 0;
    width: 100%;
    display: flex;
    gap: 6px;
  }
  .browse-toolbar .tb-right .search-inp {
    flex: 1;
    min-width: 0;
  }
}

/* ── 文件夹树 ── */
.side-tree-wrap {
  padding: 2px 4px 4px;
}
.side-tree-hd {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-text-secondary);
  padding: 2px 6px;
}
.tree-refresh {
  margin-left: auto;
  color: var(--color-primary);
  cursor: pointer;
  font-size: 11px;
}
.folder-tree {
  max-height: 280px;
  overflow-y: auto;
  font-size: 12px;
}
.folder-tree .el-tree-node__content {
  height: 26px;
}

/* ── 上传可见范围 ── */
.scope-panel {
  font-size: 12px;
}
.scope-title {
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--color-text-primary);
}
.scope-tree {
  max-height: 220px;
  overflow-y: auto;
  margin-top: 8px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 4px;
}
.scope-dl {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

/* ── 文件夹树视图（主区域）── */
.tree-panel {
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: #fff;
  padding: 10px 12px;
  margin-bottom: 12px;
}
.tree-panel-hd {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 8px;
}
.tree-panel-sub {
  font-weight: 400;
  font-size: 11px;
  color: var(--color-text-secondary);
}
.main-folder-tree {
  max-height: 55vh;
  overflow-y: auto;
  font-size: 13px;
}
.main-folder-tree .el-tree-node__content {
  height: 30px;
}
.tree-node {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
}
.tree-node-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tree-node-count {
  font-size: 11px;
  color: var(--color-text-secondary);
  margin-left: 8px;
  flex-shrink: 0;
}

/* ── 上传对话框 ── */
.up-src-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.up-src-tip {
  font-size: 11px;
  color: var(--color-text-secondary);
  margin-left: 4px;
}
.up-manifest {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 8px;
  background: #fafbfc;
}
.up-manifest-hd {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
  padding-bottom: 6px;
}
.up-manifest-group {
  border-top: 1px solid #eceff3;
  padding-top: 4px;
}
.up-manifest-group:first-child {
  border-top: none;
}
.up-manifest-group-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  font-weight: 600;
  color: #333;
  padding: 4px 4px 2px;
}
.up-manifest-list {
  max-height: 220px;
  overflow-y: auto;
}
.up-manifest-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
  color: #444;
  padding: 3px 4px;
  border-radius: 4px;
}
.up-manifest-row:nth-child(odd) {
  background: #f2f4f7;
}
.up-m-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.up-m-size {
  flex-shrink: 0;
  color: var(--color-text-secondary);
}
.up-manifest-more {
  font-size: 11px;
  color: var(--color-text-secondary);
  padding: 4px;
}
.up-manifest-empty {
  font-size: 12px;
  color: #999;
  padding: 16px 0;
  text-align: center;
  border: 1px dashed var(--color-border);
  border-radius: 8px;
}
.up-result-ok {
  font-size: 14px;
  color: var(--color-success);
  font-weight: 600;
}
.up-result-fail {
  font-size: 13px;
  color: var(--color-danger);
  font-weight: 600;
  margin-top: 8px;
}
.up-result-list {
  max-height: 180px;
  overflow-y: auto;
  font-size: 12px;
  color: #555;
  background: #fafbfc;
  border-radius: 6px;
  padding: 6px 8px;
  margin-top: 4px;
}

/* ── 文件传输 ── */
.send-file-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 8px;
}
.send-file-list {
  max-height: 160px;
  overflow-y: auto;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 6px 8px;
  margin-bottom: 8px;
}
.send-file-item {
  font-size: 12px;
  padding: 3px 0;
  border-bottom: 1px dashed #eee;
}
.send-file-item:last-child {
  border-bottom: none;
}
.send-user-tree {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 6px;
  max-height: 260px;
  overflow-y: auto;
}
.transfer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 8px;
  border-bottom: 1px solid #f0f0f0;
}
.transfer-row:last-child {
  border-bottom: none;
}
.transfer-info {
  min-width: 0;
  flex: 1;
}
.transfer-name {
  font-size: 13px;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.transfer-size {
  font-size: 11px;
  color: var(--color-text-secondary);
  margin-left: 6px;
}
.transfer-meta {
  font-size: 11px;
  color: var(--color-text-secondary);
  margin-top: 2px;
}
.transfer-acts {
  flex-shrink: 0;
  display: flex;
  gap: 6px;
}
</style>
