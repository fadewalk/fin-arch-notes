# 分布式金融架构 · 知识地图

对《分布式金融架构》课程 27 讲的蒸馏学习笔记站:交互式思维导图(markmap)、
架构/流程图(mermaid)、跨讲次专题大图、SRE 故障手册与间隔复习闪卡。

**在线访问**:https://fadewalk.github.io/fin-arch-notes/

## 仓库结构

| 路径 | 内容 |
|---|---|
| `index.html` | 构建产物:单文件学习站(内容内嵌,浏览器直接渲染) |
| `src/notes/` | 27 篇逐讲蒸馏笔记(导图/概念/要点/架构图/对比/易错/自测)+ 6 篇模块导读 |
| `src/sre/` | 9 张 SRE 故障手册卡(故障模式/观测信号/应急动作)+ 28 行监控指标速查表 |
| `src/synthesis/` | 6 张框架级大图源码:一致性阶梯、知识关联、全链路综合、3 张选型决策树 |
| `src/build_site.py` | 构建脚本:把 src/ 下的 markdown 组装为 index.html |
| `src/extract_pdfs.py` | PDF 提取脚本(原始提取文本仅存本地,不入库) |

## 重新构建

```bash
python3 src/build_site.py          # src/*.md → dist/index.html
cp dist/index.html index.html      # 发布到本仓库根目录
```

页面依赖 markmap / mermaid / marked,经 jsdelivr CDN 加载,无其他运行时依赖。
