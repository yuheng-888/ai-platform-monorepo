import{d as q,c as s,a as t,F as i,r as p,s as n,b as l,i as d,e as r,n as c,t as m}from"./index-BeRLeqXy.js";const x={class:"space-y-6"},g={class:"ui-panel"},b={class:"ui-segmented mt-6 text-xs"},f=["onClick"],v={class:"mt-6 space-y-6 text-sm text-foreground"},h={key:0,class:"space-y-6"},_={key:1,class:"space-y-6"},O=q({__name:"Docs",setup(y){const e=d("api"),a=[{id:"api",label:"API 文档"},{id:"disclaimer",label:"使用声明"}];return(w,o)=>(r(),s("div",x,[t("section",g,[o[2]||(o[2]=t("div",{class:"flex flex-wrap items-center justify-between gap-3"},[t("div",null,[t("p",{class:"ui-section-title"},"帮助中心"),t("p",{class:"mt-1 text-xs text-muted-foreground"}," 快速上手与常见问题 ")])],-1)),t("div",b,[(r(),s(i,null,p(a,u=>t("button",{key:u.id,class:c(["ui-segmented-btn flex-1 justify-center px-4 py-2",e.value===u.id?"ui-segmented-btn-active":""]),onClick:A=>e.value=u.id},m(u.label),11,f)),64))]),t("div",v,[e.value==="api"?(r(),s("div",h,[...o[0]||(o[0]=[n(`<div class="space-y-2"><p class="text-sm font-semibold">账户配置格式</p><p class="mt-1 text-xs text-muted-foreground"> accounts.json 或环境变量 ACCOUNTS_CONFIG 使用的 JSON 数组 </p><pre class="mt-3 overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-card px-4 py-3 text-xs font-mono scrollbar-slim">[
  {
    &quot;id&quot;: &quot;account_1&quot;,
    &quot;secure_c_ses&quot;: &quot;CSE.Ad...&quot;,
    &quot;csesidx&quot;: &quot;498...&quot;,
    &quot;config_id&quot;: &quot;0cd...&quot;,
    &quot;host_c_oses&quot;: &quot;&quot;,
    &quot;expires_at&quot;: &quot;2026-12-31 23:59:59&quot;
  }
]</pre><p class="mt-2 text-xs text-muted-foreground"> 必填：secure_c_ses / csesidx / config_id。id、host_c_oses、expires_at 可选。 </p></div><div class="space-y-2"><p class="text-sm font-semibold">API 对话 curl 格式</p><p class="mt-1 text-xs text-muted-foreground"> 标准的 OpenAI 兼容格式，支持流式和非流式输出。 </p><div class="mt-3"><pre class="overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-card px-4 py-3 text-xs font-mono scrollbar-slim">curl -X POST &quot;http://localhost:7860/v1/chat/completions&quot; \\
  -H &quot;Content-Type: application/json&quot; \\
  -H &quot;Authorization: Bearer YOUR_API_KEY&quot; \\
  -d &#39;{
    &quot;model&quot;: &quot;gemini-2.5-flash&quot;,
    &quot;stream&quot;: false,
    &quot;temperature&quot;: 0.7,
    &quot;top_p&quot;: 1,
    &quot;messages&quot;: [
      { &quot;role&quot;: &quot;system&quot;, &quot;content&quot;: &quot;你是一个简洁的助手&quot; },
      { &quot;role&quot;: &quot;user&quot;, &quot;content&quot;: &quot;你好，介绍一下这个项目&quot; }
    ]
  }&#39;</pre></div><p class="mt-2 text-xs text-muted-foreground"> 如果未设置 API Key，可省略 Authorization。 </p></div><div class="space-y-2"><p class="text-sm font-semibold">文生图格式（Base64 / URL 输出）</p><p class="mt-1 text-xs text-muted-foreground"> 使用支持文生图的模型，直接给文本提示即可；输出格式由系统设置决定（base64 或 url）。 </p><pre class="mt-3 overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-card px-4 py-3 text-xs font-mono scrollbar-slim">curl -X POST &quot;http://localhost:7860/v1/chat/completions&quot; \\
  -H &quot;Content-Type: application/json&quot; \\
  -H &quot;Authorization: Bearer YOUR_API_KEY&quot; \\
  -d &#39;{
    &quot;model&quot;: &quot;gemini-3-pro-preview&quot;,
    &quot;stream&quot;: true,
    &quot;temperature&quot;: 0.7,
    &quot;top_p&quot;: 1,
    &quot;messages&quot;: [
      { &quot;role&quot;: &quot;user&quot;, &quot;content&quot;: &quot;生成一只戴着头盔的猫，赛博风格&quot; }
    ]
  }&#39;</pre></div><div class="space-y-2"><p class="text-sm font-semibold">专用图片生成（gemini-imagen）</p><p class="mt-1 text-xs text-muted-foreground"> 使用 gemini-imagen 虚拟模型强制启用图片生成功能，输出格式由系统设置决定（base64 或 url）。 </p><pre class="mt-3 overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-card px-4 py-3 text-xs font-mono scrollbar-slim">curl -X POST &quot;http://localhost:7860/v1/chat/completions&quot; \\
  -H &quot;Content-Type: application/json&quot; \\
  -H &quot;Authorization: Bearer YOUR_API_KEY&quot; \\
  -d &#39;{
    &quot;model&quot;: &quot;gemini-imagen&quot;,
    &quot;stream&quot;: true,
    &quot;messages&quot;: [
      { &quot;role&quot;: &quot;user&quot;, &quot;content&quot;: &quot;生成一只可爱的猫咪，卡通风格&quot; }
    ]
  }&#39;</pre></div><div class="space-y-2"><p class="text-sm font-semibold">专用视频生成（gemini-veo）</p><p class="mt-1 text-xs text-muted-foreground"> 使用 gemini-veo 虚拟模型生成视频，输出格式由系统设置决定（html/url/markdown）。 </p><pre class="mt-3 overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-card px-4 py-3 text-xs font-mono scrollbar-slim">curl -X POST &quot;http://localhost:7860/v1/chat/completions&quot; \\
  -H &quot;Content-Type: application/json&quot; \\
  -H &quot;Authorization: Bearer YOUR_API_KEY&quot; \\
  -d &#39;{
    &quot;model&quot;: &quot;gemini-veo&quot;,
    &quot;stream&quot;: true,
    &quot;messages&quot;: [
      { &quot;role&quot;: &quot;user&quot;, &quot;content&quot;: &quot;生成一段可爱猫咪玩耍的视频&quot; }
    ]
  }&#39;</pre></div><div class="space-y-2"><p class="text-sm font-semibold">图生图格式（Base64 / URL 输入）</p><p class="mt-1 text-xs text-muted-foreground"> content 使用多模态数组，image_url 可填 URL 或 data:base64。 </p><div class="mt-3 grid gap-3 md:grid-cols-2"><pre class="overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-card px-4 py-3 text-xs font-mono scrollbar-slim">curl -X POST &quot;http://localhost:7860/v1/chat/completions&quot; \\
  -H &quot;Content-Type: application/json&quot; \\
  -H &quot;Authorization: Bearer YOUR_API_KEY&quot; \\
  -d &#39;{
    &quot;model&quot;: &quot;gemini-3-flash-preview&quot;,
    &quot;stream&quot;: false,
    &quot;temperature&quot;: 0.7,
    &quot;top_p&quot;: 1,
    &quot;messages&quot;: [
      {
        &quot;role&quot;: &quot;user&quot;,
        &quot;content&quot;: [
          { &quot;type&quot;: &quot;text&quot;, &quot;text&quot;: &quot;把图片改成插画风格&quot; },
          { &quot;type&quot;: &quot;image_url&quot;, &quot;image_url&quot;: { &quot;url&quot;: &quot;https://example.com/cat.png&quot; } }
        ]
      }
    ]
  }&#39;</pre><pre class="overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-card px-4 py-3 text-xs font-mono scrollbar-slim">curl -X POST &quot;http://localhost:7860/v1/chat/completions&quot; \\
  -H &quot;Content-Type: application/json&quot; \\
  -H &quot;Authorization: Bearer YOUR_API_KEY&quot; \\
  -d &#39;{
    &quot;model&quot;: &quot;gemini-3-flash-preview&quot;,
    &quot;stream&quot;: false,
    &quot;temperature&quot;: 0.7,
    &quot;top_p&quot;: 1,
    &quot;messages&quot;: [
      {
        &quot;role&quot;: &quot;user&quot;,
        &quot;content&quot;: [
          { &quot;type&quot;: &quot;text&quot;, &quot;text&quot;: &quot;增强画面细节&quot; },
          { &quot;type&quot;: &quot;image_url&quot;, &quot;image_url&quot;: { &quot;url&quot;: &quot;data:image/png;base64,AAA...&quot; } }
        ]
      }
    ]
  }&#39;</pre></div></div><div class="space-y-2"><p class="text-sm font-semibold">读文件格式（URL / Base64）</p><p class="mt-1 text-xs text-muted-foreground"> 适用于 PDF/图片/文本等可读文件，Word/PPT 等可能不支持会被提示转换。大部分文件都可能支持，建议自行测试。 </p><div class="mt-3 grid gap-3 md:grid-cols-2"><pre class="overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-card px-4 py-3 text-xs font-mono scrollbar-slim">curl -X POST &quot;http://localhost:7860/v1/chat/completions&quot; \\
  -H &quot;Content-Type: application/json&quot; \\
  -H &quot;Authorization: Bearer YOUR_API_KEY&quot; \\
  -d &#39;{
    &quot;model&quot;: &quot;gemini-2.5-pro&quot;,
    &quot;stream&quot;: false,
    &quot;temperature&quot;: 0.7,
    &quot;top_p&quot;: 1,
    &quot;messages&quot;: [
      {
        &quot;role&quot;: &quot;user&quot;,
        &quot;content&quot;: [
          { &quot;type&quot;: &quot;text&quot;, &quot;text&quot;: &quot;读取并总结这个文件&quot; },
          { &quot;type&quot;: &quot;image_url&quot;, &quot;image_url&quot;: { &quot;url&quot;: &quot;https://example.com/doc.pdf&quot; } }
        ]
      }
    ]
  }&#39;</pre><pre class="overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-card px-4 py-3 text-xs font-mono scrollbar-slim">curl -X POST &quot;http://localhost:7860/v1/chat/completions&quot; \\
  -H &quot;Content-Type: application/json&quot; \\
  -H &quot;Authorization: Bearer YOUR_API_KEY&quot; \\
  -d &#39;{
    &quot;model&quot;: &quot;gemini-2.5-pro&quot;,
    &quot;stream&quot;: false,
    &quot;temperature&quot;: 0.7,
    &quot;top_p&quot;: 1,
    &quot;messages&quot;: [
      {
        &quot;role&quot;: &quot;user&quot;,
        &quot;content&quot;: [
          { &quot;type&quot;: &quot;text&quot;, &quot;text&quot;: &quot;读取并摘要&quot; },
          { &quot;type&quot;: &quot;image_url&quot;, &quot;image_url&quot;: { &quot;url&quot;: &quot;data:application/pdf;base64,AAA...&quot; } }
        ]
      }
    ]
  }&#39;</pre></div></div>`,7)])])):l("",!0),e.value==="disclaimer"?(r(),s("div",_,[...o[1]||(o[1]=[n('<div class="space-y-2"><p class="text-sm font-semibold">使用声明与免责条款</p><div class="mt-3 space-y-3 text-xs text-muted-foreground leading-relaxed"><div class="rounded-2xl border border-rose-200 bg-rose-50 p-4"><p class="font-medium text-rose-600">⚠️ 严禁滥用：禁止将本工具用于商业用途或任何形式的滥用（无论规模大小）</p></div><div class="rounded-2xl border border-border bg-muted/30 p-4"><p class="font-medium text-foreground">本工具严禁用于以下行为：</p><ul class="mt-2 space-y-1 pl-4"><li>• 商业用途或盈利性使用</li><li>• 任何形式的批量操作或自动化滥用（无论规模大小）</li><li>• 破坏市场秩序或恶意竞争</li><li>• 违反 Google 服务条款的任何行为</li><li>• 违反 Microsoft 服务条款的任何行为</li></ul></div><div class="rounded-2xl border border-border bg-muted/30 p-4"><p class="font-medium text-foreground">违规后果</p><p class="mt-2">滥用行为可能导致账号永久封禁、法律追责，一切后果由使用者自行承担。</p></div><div class="rounded-2xl border border-border bg-muted/30 p-4"><p class="font-medium text-foreground">📖 合法用途</p><p class="mt-2">本项目仅限于以下场景：</p><ul class="mt-2 space-y-1 pl-4"><li>• 个人学习与技术研究</li><li>• 浏览器自动化技术探索</li><li>• 非商业性技术交流</li></ul></div><div class="rounded-2xl border border-border bg-muted/30 p-4"><p class="font-medium text-foreground">⚖️ 法律责任</p><ul class="mt-2 space-y-2 pl-4"><li><strong>使用者责任：</strong>使用本工具产生的一切后果（包括但不限于账号封禁、数据损失、法律纠纷）由使用者完全承担</li><li><strong>合规义务：</strong>使用者必须遵守所在地法律法规及第三方服务条款（包括但不限于 Google Workspace、Microsoft 365 等服务条款）</li><li><strong>作者免责：</strong>作者不对任何违规使用、滥用行为或由此产生的后果承担责任</li></ul></div><div class="rounded-2xl border border-border bg-muted/30 p-4"><p class="font-medium text-foreground">📋 技术声明</p><ul class="mt-2 space-y-1 pl-4"><li>• <strong>无担保：</strong>本项目按&quot;现状&quot;提供，不提供任何形式的担保</li><li>• <strong>第三方依赖：</strong>依赖的第三方服务（如 DuckMail API、Microsoft Graph API 等）可用性不受作者控制</li><li>• <strong>维护权利：</strong>作者保留随时停止维护、变更功能或关闭项目的权利</li></ul></div><div class="rounded-2xl border border-border bg-muted/30 p-4"><p class="font-medium text-foreground">🔗 相关服务条款</p><p class="mt-2">使用本工具时，您必须同时遵守以下第三方服务的条款：</p><ul class="mt-2 space-y-1 pl-4"><li>• <a href="https://policies.google.com/terms" target="_blank" class="text-primary hover:underline">Google 服务条款</a></li><li>• <a href="https://workspace.google.com/terms/service-terms.html" target="_blank" class="text-primary hover:underline">Google Workspace 附加条款</a></li><li>• <a href="https://www.microsoft.com/servicesagreement" target="_blank" class="text-primary hover:underline">Microsoft 服务协议</a></li><li>• <a href="https://www.microsoft.com/licensing/terms" target="_blank" class="text-primary hover:underline">Microsoft 365 使用条款</a></li></ul></div><div class="rounded-2xl border border-amber-200 bg-amber-50 p-4"><p class="font-medium text-amber-700">使用本工具即表示您已阅读、理解并同意遵守以上所有条款。</p></div></div></div>',1)])])):l("",!0)])])]))}});export{O as default};
