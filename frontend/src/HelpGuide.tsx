export default function HelpGuide(){
  return <>
    <h2>系统简介</h2>
    <p>把户型图传进来，在图上规划设备点位，给点位配上知识库里的产品，最后生成产品清单和客户报价。适合大平层、别墅、排屋等有线智能项目。</p>

    <h3>一页速查 · 照着做一遍就会</h3>
    <ol className="manual-steps">
      <li><b>建项目</b><span>项目页点「新建项目」，填名称、客户、地址。</span></li>
      <li><b>选工作区</b><span>依次选楼层、主图纸和当前图层；可以额外勾选其他图层叠加查看。新点位只进入当前图层。</span></li>
      <li><b>布点位</b><span>用左侧设备工具或快捷键选设备，在图上点击或拖拽。</span></li>
      <li><b>配产品</b><span>点选点位，在右侧详情里选产品；图纸做完也能在报价页直接加。</span></li>
      <li><b>出报价</b><span>报价页核对数量、单价、备注，导出 Excel、PPTX 或 PDF。</span></li>
    </ol>
    <div className="manual-keybar">
      <span><kbd>A</kbd>选择 / 框选</span>
      <span><kbd>Space</kbd>按住临时拖画布</span>
      <span><kbd>Q</kbd>开关</span>
      <span><kbd>W</kbd>窗帘</span>
      <span><kbd>E</kbd>摄像头</span>
      <span><kbd>R</kbd>调光</span>
      <span><kbd>S</kbd>人体传感器</span>
      <span><kbd>D</kbd>温控器</span>
      <span><kbd>F</kbd>门禁</span>
      <span><kbd>G</kbd>吸顶 AP</span>
      <span><kbd>H</kbd>墙面 AP</span>
      <span><kbd>J</kbd>水浸</span>
      <span><kbd>K</kbd>影音</span>
      <span><kbd>L</kbd>智能系统</span>
      <span><kbd>M</kbd>其他设备</span>
      <span><kbd>T</kbd>非智能区域</span>
      <span><kbd>Esc</kbd>退出布点</span>
      <span><kbd>Delete</kbd>删除</span>
      <span><kbd>Ctrl/Cmd Z</kbd>撤销</span>
      <span><kbd>Ctrl/Cmd Shift Z</kbd>恢复</span>
    </div>

    <h3>完整手册</h3>

    <details className="manual-chapter" open>
      <summary>1. 启动工具</summary>
      <div className="manual-body">
        <ul>
          <li><b>Mac</b>：双击工具根目录的 <kbd>start-mac.command</kbd>，或在终端执行该文件路径；支持项目位于已挂载的 NAS 共享目录，浏览器会自动打开。</li>
          <li><b>Windows</b>：从 GitHub Releases 下载版本 ZIP，解压到本机固定磁盘，再双击 <kbd>start-windows.bat</kbd>。若工具文件夹里有 <kbd>data</kbd> 文件夹，就使用便携数据；否则使用当前 Windows 用户的本机数据目录。</li>
          <li><b>运行范围</b>：应用仅在本机打开。数据可手动复制到另一台电脑，但不会自动同步；不要在多台电脑同时打开同一份便携数据。Mac 从 NAS 启动时仍使用 Mac 本机数据。</li>
        </ul>
        <p className="manual-warn">打开后先看两个地方：左上角显示的版本号，以及右上角是否显示「版本已同步」。如果出现红色版本提示，说明前后端不一致，关掉重开一次工具。</p>
        <p className="manual-warn">Mac 从 NAS 运行时，NAS 只提供程序文件；业务数据保存在本机。Mac/Windows 从本机工具目录启动时，若同级有 <code>data/</code> 则改用该目录，方便手动搬运。更新便携数据时，要把整个 <code>data/</code> 复制到新版本工具目录。请勿同时打开同一份便携数据。</p>
      </div>
    </details>

    <details className="manual-chapter">
      <summary>2. 建项目</summary>
      <div className="manual-body">
        <ul>
          <li>项目页点「新建项目」，填项目名称、客户、地址。状态默认「进行中」。</li>
          <li>项目页像电脑文件管理器一样使用：新建文件夹后，拖动项目卡片到文件夹即可归档；点击文件夹可打开查看。打开文件夹后可把项目拖到“移出文件夹”区域。重命名文件夹不会影响项目；删除文件夹只会把其中项目移回全部项目，不会删除项目。</li>
          <li>项目卡片右上角：铅笔按钮改项目资料，复制按钮复制完整项目（包括楼层、图纸、图层、点位、报价明细、费用和历史版本），垃圾桶按钮删项目。副本图纸文件独立保存，产品库仍为共用。</li>
          <li>卡片上的「已签」勾选框用来标记方案已签约；已签卡片以稍深的浅绿色区分，不影响其他状态。可勾选「只查看已签项目」筛选已签项目。</li>
        </ul>
        <p className="manual-warn">删项目会连带清掉这个项目的图纸、点位和报价，但不会删知识库里的产品。删之前想清楚。</p>
      </div>
    </details>

    <details className="manual-chapter">
      <summary>3. 上传图纸</summary>
      <div className="manual-body">
        <ul>
          <li>支持 JPG、PNG、PDF。PDF 要先填页码再上传，服务器会把那一页渲染成可编辑背景。</li>
          <li>每个新楼层对应一张横向 16:9 白色画布，画布中有一张主图纸；上传会填入或替换当前楼层的主图纸。</li>
          <li>旧项目中原有多张图纸的楼层仍可通过图纸选择器切换，每张图纸和点位都会保留。</li>
          <li>新画布上可拖动、缩放或每次旋转主图纸；点位会跟随图纸。点「裁剪」后会显示完整原图和上次的虚线框；拖边/角控制点调整大小，拖框内移动位置，然后点「应用裁剪」。裁剪区域必须完整包含现有点位。再次进入仍能调整；「恢复原图」可恢复全幅。原图始终保留，裁剪前请将主图纸旋转回 0°。</li>
        </ul>
        <p>图纸上方选择楼层和主图纸；右侧「图层」面板用于选择当前图层、切换图层显示、锁定、重命名、新增和删除。当前图层决定新点位归属；显示多个图层时可叠加查看。历史多图纸楼层继续保留切换入口，旧点位不会迁移或合并。</p>
        <p>从画布上边缘拖出垂直参考线、从左边缘拖出水平参考线；拖动参考线可调整位置，并吸附画布边缘、中心、设备点位和其他参考线。双击参考线可删除单条，参考线菜单可清除全部。主图纸缩放、旋转和裁剪操作位于图纸选择旁，PDF 上传前先设置页码。</p>
        <p className="manual-warn">切换楼层、图纸或图层后，看不到原来的点位通常是因为正在看另一处；切回原来的楼层、图纸和图层即可。删除图层会连同其中设备一起删除，请先核对当前选择。</p>
      </div>
    </details>

    <details className="manual-chapter">
      <summary>4. 布点位</summary>
      <div className="manual-body">
        <p>先用左侧工具或快捷键选一种设备，然后在图上点击（点状设备）或按住拖动（带方向的设备）。选好之后可以连续布点，按 <kbd>Esc</kbd>、点右键或换一个工具就退出。</p>
        <ul>
          <li><b>智能开关</b>：选择开关工具后直接在图纸上布点；产品可随后在右侧点位详情中关联。</li>
          <li><b>窗帘</b>：按住拖动设置符号初始长度；画布滚轮缩放时，窗帘电机、线段和波浪线与画布等比例缩放。选中点位后可在详情中修改电机大小、符号长度、线宽或隐藏电机，拖动端点也会更新长度。单开是一条向右箭头；对开是两条等长、箭头相向的线；双层单开是上方波浪线和下方直线，两条都向右；双层对开则让这两条轨道都从两端向中间对开。两个双层样式的波浪弧度相同，电机只显示在起点。</li>
          <li><b>摄像头</b>：按住拖动，起点是摄像头位置，拖到哪就代表朝哪、看多远，会生成两条边界线和半透明扇形。选中后拖终点手柄能改方向和距离，详情里能调监控角度（10°～180°，默认 60°）。</li>
          <li><b>设备图标</b>：图纸、左侧工具和图例使用相同图形。白底浅阴影表示设备位置；开关、墙面 AP 用圆角方框，其他点状设备用圆框。图纸上可在右侧详情调整大小和颜色。</li>
          <li><b>调光区域</b>：按住拖出一个范围。选中后拖四个角能缩放，拖中间能整体移动。相同颜色的重叠区域会连成一个外形，重叠处不重复显示边线或加深颜色；各个区域仍可分别选中编辑。</li>
          <li><b>非智能区域</b>：同样框选，用灰色虚线斜纹表示；相同颜色的重叠范围会合并显示。它只是图纸上的标注，<b>不关联产品、不计数、不进报价</b>。</li>
          <li><b>多选</b>：按住 <kbd>Shift</kbd> 点多个点位；选择工具下在空白处拖动即可框选，按住 <kbd>Shift</kbd> 可追加框选。选中多个同类点位后能一次性配同一个产品。</li>
          <li><b>看图纸</b>：滚轮缩放；使用「拖动画布」工具或按住 <kbd>Space</kbd> 可以临时拖动画布，松开自动回到原来的工具，拖的时候不会误加点位。</li>
          <li><b>图例</b>：图纸出现点位后会自动生成图例，同一种设备只列一次；新增或删掉最后一个同类点位会自动更新。每个图例项都可以独立拖动；按住「移动全部图例」可以整体移动，保存重开和导出 PNG/PDF 都会保持。</li>
          <li><b>撤销</b>：<kbd>Ctrl/Cmd Z</kbd> 撤销，<kbd>Ctrl/Cmd Shift Z</kbd> 恢复。注意撤销只在当前这次编辑里有效，刷新页面后历史清空。</li>
        </ul>
        <p className="manual-warn">区域盖住设备的时候，点设备选中的是设备；只有点区域的空白处才会选中区域。要是想选区域，别点在设备上。</p>
        <p>新增点位会先立即显示在图纸上并保存到这台电脑的数据目录。项目和产品笔记保存在本机，不进行实时 NAS 同步；不要因为网络状态重复点击同一位置。</p>
        <p>顶部「快捷键」按钮里可以改所有工具的按键。设了重复的键会报错并且不保存，「Space」是保留键不能占用。改完点保存，恢复默认也在里面。</p>
      </div>
    </details>

    <details className="manual-chapter">
      <summary>5. 点位详情与批量配置</summary>
      <div className="manual-body">
        <ul>
          <li>选中点位后，右侧能改名称、房间、数量、备注，也能换产品、锁定（锁住后不会误拖动）、设显示颜色。</li>
          <li>名称、房间、备注、单价这些输入框，<b>光标移开就自动保存</b>；数量、图标大小、窗帘线宽、颜色和监控角度连续修改时会在约 800ms 后合并保存，避免共享盘反复写入。右上角会显示保存状态。</li>
          <li>选中多个同类型点位，可以批量配同一个产品，不用一个个点。</li>
          <li>点位可以复制、删除、撤销恢复。按 <kbd>Ctrl/Cmd C</kbd> 后将鼠标移到图纸目标位置，再按 <kbd>Ctrl/Cmd V</kbd> 粘贴。</li><li>新设备默认大小 20，数值框和滑块可以双向调节；窗帘使用独立的线条粗细数值框与滑块。</li><li>「其他设备」可以自定义名称，并从全部产品中选择关联；类型本身仍是「其他设备」。</li>
        </ul>
      </div>
    </details>

    <details className="manual-chapter">
      <summary>6. 产品库</summary>
      <div className="manual-body">
        <p>产品库与知识库目录按<b>所属系统</b>管理；旧「智能、影音、灯光、网络」只作为历史兼容字段保留。</p>
        <p className="manual-warn">有两个容易搞混的字段，一定要分清：<br/><b>适用点位</b>决定这个产品能配到图纸上哪种符号（开关、窗帘、传感器、吸顶 AP……）；<br/><b>所属系统</b>决定报价时它归到哪个系统（中控、灯控、电动窗帘……）。两者互不影响，填错了图纸或报价就会错位。</p>
        <ul>
          <li><b>产品笔记</b>：每款产品对应本机数据目录 <code>01_产品库/所属系统中文名</code> 里的一篇笔记，无法确认系统时放在「未分类」；旧「智能/影音/灯光/网络」只作历史兼容。在网页上新增、编辑、停用或删除产品时，会更新这台电脑上的笔记。其他电脑不会自动获得这些修改。</li>
          <li><b>导入</b>：支持 CSV（UTF-8）和 XLSX。列名顺序为「品牌, 产品名称, 分类, 点位类型, 所属系统, 售价, 进货价, 产地, 单位, 参数, 说明」。必填是品牌、产品名称、分类、售价；进货价和产地可以空着。导入前会整批校验，只要有一行错就全部不入库。</li>
          <li><b>批量操作</b>：勾选多款产品后可以批量改分类、启用、停用、删除。</li>
          <li><b>品牌库</b>：可以给品牌上传 Logo，优先 SVG，其次透明背景 PNG。报价单上的品牌列会优先显示 Logo，没有 Logo 才显示文字。</li>
          <li><b>产品图片</b>：在产品编辑页单独上传，白底显示，透明通道会保留。</li>
        </ul>
        <p className="manual-warn">进货价默认是隐藏的。要显示，双击产品库右下角那个几乎看不见的小方块（18×18 像素），再双击一次关掉。每次重新进产品库都会自动回到隐藏状态——客户在旁边看屏幕时不用担心。</p>
      </div>
    </details>

    <details className="manual-chapter">
      <summary>7. 报价</summary>
      <div className="manual-body">
        <p>报价系统按以下顺序排列：设备柜体、中控、触控、遮阳、暖通、线材、UBNT网络监控、可视对讲、网络、监控、背景音乐、灯控。UBNT网络监控系统用于归类可视对讲、网络及监控相关的 UBNT 设备；既有分类保留。没有报价产品的系统默认隐藏，序号自动补位；产品没填所属系统的会落到「未分类」。</p>
        <ul>
          <li>产品清单有两种看法：看单条明细，或看「相同产品＋相同项目单价」合并后的汇总。</li>
          <li>产品小计、服务费、系统总计在产品表格末尾，不是单独一块。</li>
          <li><b>直接添加产品</b>：图纸做完之后还能在报价页按分类和关键词搜产品，勾选多款一次加入。这些不关联图纸，会标成「清单加项」。加进去以后能单独改数量、项目单价和明细备注。</li>
          <li><b>替换产品</b>：编辑模式每行最左侧的替换按钮会打开产品库，选中后将当前报价行资料替换为新产品资料，数量重置为 1；不修改图纸上的点位。</li>
          <li><b>跨页排序</b>：编辑模式拖动产品行，可在同一系统的不同分页间排序；切页或重新打开后仍保留。</li>
          <li><b>服务费</b>：每个系统可以单独设，按比例算或按固定金额算。</li>
          <li><b>施工调试费</b>：右上角入口设置强电施工、弱电施工、设备安装调试、线路材料费、系统调试及培训金额；非零费用显示在报价最后，计入总额但不参与折扣和税额。零金额不出现在目录、明细或汇总。</li>
          <li><b>报价版本</b>：点右上角「报价版本」可保存包含产品明细、价格、数量、系统服务费和施工调试费的完整快照。选择「读取此版本」会将当时内容应用到当前报价，操作前会提示覆盖当前报价；快照仍保留。可删除单个版本，删除后不能恢复，当前报价不受影响。</li>
        </ul>
        <p>导出有三种：<b>Excel 清单</b>、<b>可编辑 PPTX</b>、<b>PDF 客户报价</b>。PPTX 是 16:9 横版，产品多的时候自动分页，里面每个标题、单元格、图片、金额都是独立对象，可以在 PowerPoint 或 WPS 里继续改。图纸页还能单独导出点位图 PDF。</p>
        <p className="manual-warn">金额在数据库里是按「分」保存的，界面显示两位小数。改过数量或单价后，点位会自动记住你的修改，不会再被图纸数量覆盖；想还原成图纸数量，点「恢复图纸数量」。</p>
      </div>
    </details>

    <details className="manual-chapter">
      <summary>8. 数据存在哪 · 怎么备份</summary>
      <div className="manual-body">
        <p>项目、产品、品牌、点位和报价保存在当前选中的数据目录，SQLite 是运行数据库。本机工具目录旁如果有 <code>data/</code>，Mac/Windows 会使用它；没有时，Mac 回退到 <code>~/Library/Application Support/TaiyuanPointQuote/data/</code>，Windows 回退到 <code>%LOCALAPPDATA%\TaiyuanPointQuote\data\</code>。Mac 从 NAS 启动始终使用 Mac 本机数据目录。GitHub 下载包不包含业务数据。</p>
        <ul>
          <li>产品和品牌 → 本机数据目录 <code>01_产品库</code></li>
          <li>项目、图纸、点位、报价 → 本机数据目录 <code>06_客户档案/智能图纸与报价</code></li>
          <li>产品图片和品牌 Logo → 本机数据目录 <code>09_附件</code></li>
          <li>原始图纸、导出文件与 SQLite → 本机数据目录</li>
        </ul>
        <p className="manual-warn">版本下载包不含 <code>data/</code>。要在两台电脑之间转移数据，请先关闭工具，复制整个 <code>data/</code> 文件夹，在目标电脑解压后的工具根目录旁粘贴。更新到新版本时，也要把整个文件夹复制到新版本工具目录。若目标工具目录没有 <code>data/</code>，程序会使用本机数据目录。更换或合并数据前请先备份；不要同时打开同一份数据。</p>
        <p>Mac 从 NAS 启动时不会使用 NAS 中的 <code>data/</code>，而会继续使用这台 Mac 的本机数据。NAS 不在线时不能从 NAS 启动。</p>
      </div>
    </details>

    <details className="manual-chapter">
      <summary>9. 常见问题</summary>
      <div className="manual-body">
        <ul>
          <li><b>点位加不上 / 点上去没反应</b>：先确认是不是还在布点模式（换工具或按 Esc 会退出）。另外检查是不是点在锁定的点位上。</li>
          <li><b>想选中的区域总选到设备</b>：这是故意的，设备优先于区域。要选区域就点区域的空白处。</li>
          <li><b>PDF 图纸只有第一页</b>：上传的时候要填页码，一次传一页。</li>
          <li><b>换了图纸点位不见了</b>：点位绑定在各自的图纸上，切换图纸只显示当前这张的。</li>
          <li><b>报价里品牌只显示文字没有 Logo</b>：到品牌库给这个品牌上传 Logo。</li>
          <li><b>进货价那列不见了</b>：本来就是默认隐藏的，双击产品库右下角的小方块。</li>
          <li><b>Windows 启动失败</b>：确认工具程序位于本机固定磁盘，并从根目录双击 <code>start-windows.bat</code>。先检查启动窗口提示；详细日志位于 <code>%TEMP%\PointQuote-startup.log</code>，诊断日志位于 <code>%LOCALAPPDATA%\TaiyuanPointQuote\logs\diagnostics.jsonl</code>。</li>
          <li><b>右上角红色版本提示</b>：前后端版本不一致，关掉工具重开。</li>
          <li><b>多台电脑数据对不上</b>：不要同时开。约定好只有一台在写。</li>
        </ul>
      </div>
    </details>

    <details className="manual-chapter">
      <summary>10. 快捷键总表</summary>
      <div className="manual-body">
        <table className="manual-table">
          <thead><tr><th>按键</th><th>作用</th></tr></thead>
          <tbody>
            <tr><td>A</td><td>选择 / 框选工具（默认工具）</td></tr>
            <tr><td>Q</td><td>智能开关（直接布点）</td></tr>
            <tr><td>W</td><td>窗帘（拖出电机与方向）</td></tr>
            <tr><td>E</td><td>摄像头（拖出方向与距离）</td></tr>
            <tr><td>R</td><td>调光</td></tr>
            <tr><td>T</td><td>非智能区域</td></tr>
            <tr><td>S</td><td>人体传感器</td></tr>
            <tr><td>D</td><td>温控器</td></tr>
            <tr><td>F</td><td>智能门禁</td></tr>
            <tr><td>G</td><td>吸顶 AP</td></tr>
            <tr><td>H</td><td>墙面 AP</td></tr>
            <tr><td>J</td><td>水浸传感器</td></tr>
            <tr><td>K</td><td>影音设备</td></tr>
            <tr><td>L</td><td>智能系统</td></tr>
            <tr><td>M</td><td>其他设备</td></tr>
            <tr><td>Space（按住）</td><td>临时拖动画布，松开恢复原工具</td></tr>
            <tr><td>Esc</td><td>退出布点 / 取消当前操作</td></tr>
            <tr><td>右键</td><td>退出布点</td></tr>
            <tr><td>Delete</td><td>删除选中的点位</td></tr>
            <tr><td>Ctrl/Cmd Z</td><td>撤销</td></tr>
            <tr><td>Ctrl/Cmd Shift Z</td><td>恢复</td></tr>
            <tr><td>Shift + 点击</td><td>加选 / 减选点位</td></tr>
            <tr><td>空白拖动</td><td>框选；Shift 可追加</td></tr>
          </tbody>
        </table>
        <p>以上按键都可以在顶部「快捷键」里改成自己习惯的，只有 <kbd>Space</kbd> 是固定保留键。文本框、搜索框、价格框里有光标时，字母快捷键不会切工具。</p>
      </div>
    </details>
  </>;
}
