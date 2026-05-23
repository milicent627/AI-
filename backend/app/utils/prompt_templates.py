SYSTEM_PROMPT = """你是一位专业的华语小说家，擅长创作引人入胜的小说内容。你的写作具有以下特点：
- 文笔流畅自然，避免AI生成的生硬感
- 善用细节描写和感官描写增强画面感
- 对话符合角色性格，生动自然
- 情节推进有节奏感，张弛有度
- 善于埋设伏笔和前后呼应"""

CONTINUATION_SYSTEM = SYSTEM_PROMPT + """

续写规则：
1. 严格承接上文内容，保持情节连贯
2. 保持已有角色的性格、言行一致
3. 遵循指定的风格指南和剧情方向
4. 新增内容应与已有的世界设定一致
5. 在合适的位置自然推进剧情"""

CONTINUATION_USER = """{context}

{instruction}

请根据以上内容进行续写："""

DIRECTED_CONTINUATION_USER = """{context}

续写方向要求：{direction}
目标字数：约{target_words}字
风格要求：{style_guide}

请根据以上要求进行定向续写："""

BRANCH_CONTINUATION_USER = """{context}

从以下分叉点开始，走向不同的剧情发展：
分叉点：{branch_point}
分支方向：{branch_direction}
目标字数：约{target_words}字

请写出这个分支的剧情发展："""

SUMMARY_SMALL_PROMPT = """请将以下小说章节内容压缩为简洁的情节摘要（200-400字）。
保留：关键情节转折、重要对话、角色行为动机、新出现的设定。
忽略：环境渲染细节、打斗过程、内心独白的展开部分。

章节内容：
{chapter_content}

请输出简洁摘要："""

SUMMARY_LARGE_PROMPT = """请将以下多段小总结整合为一个完整的故事大纲（500-800字）。
保留：主线剧情走向、重大事件、角色成长弧线、世界观关键信息。
按照时间线组织，确保逻辑连贯。

小总结列表：
{small_summaries}

请输出整合后的大总结："""

WORLD_ANALYSIS_PROMPT = """请分析以下新增章节内容，提取所有世界观相关信息。
请以JSON格式输出，包含以下字段：

{{
  "new_characters": [
    {{
      "name": "角色名",
      "aliases": ["别名"],
      "gender": "男/女/未知",
      "age": "年龄或年龄范围",
      "appearance": "外貌描述",
      "identity": "身份/职业",
      "personality": ["性格标签"],
      "abilities": ["能力/技能"],
      "catchphrases": ["口头禅"],
      "importance": 1-5,
      "description": "角色简介"
    }}
  ],
  "updated_characters": [
    {{
      "name": "已有角色名",
      "changes": "变化描述",
      "new_abilities": ["新能力"],
      "status_change": "状态变化",
      "new_relationships": [{{"target": "对方角色", "type": "关系类型", "description": "关系描述"}}]
    }}
  ],
  "new_locations": [{{"name": "地点名", "description": "描述", "features": ["特征"]}}],
  "new_factions": [{{"name": "势力名", "description": "描述", "members": ["成员"]}}],
  "new_items": [{{"name": "物品名", "description": "描述", "significance": "重要性"}}],
  "world_rules": ["新的世界观规则"],
  "potential_foreshadowings": [{{"title": "伏笔标题", "description": "描述", "related_characters": ["相关角色"]}}]
}}

章节内容：
{chapter_content}

只输出JSON，不要其他内容："""

POLISHING_SYSTEM = """你是一位资深华语文学编辑。你的任务是将文本打磨为自然流畅的中文小说。
规则：
1. 去掉"首先/其次/最后/总而言之/此外/与此同时"等AI惯用连接词
2. 增加细节描写，减少抽象概括
3. 对话要符合角色性格，有口语感
4. 动作和神态穿插在对话中
5. 长短句交错，控制节奏
6. 保持原文情节和意思完全不变，只优化表达
7. 不要增加新剧情，不要删除任何关键信息"""

POLISHING_USER = """请润色以下文本：

{text}

润色后输出："""

FORESHADOWING_DETECTION = """请分析以下新增章节，检测与伏笔相关的内容：

已有伏笔列表：
{existing_foreshadowings}

新增章节内容：
{chapter_content}

请以JSON格式输出：
{{
  "new_foreshadowings": [
    {{"title": "新伏笔标题", "description": "伏笔内容", "priority": 1-5, "related_characters": ["相关角色"]}}
  ],
  "progressed_foreshadowings": [
    {{"id": "已有伏笔ID或标题", "progress": "推进情况描述"}}
  ],
  "revealed_foreshadowings": [
    {{"id": "已有伏笔ID或标题", "reveal_description": "揭示方式"}}
  ]
}}

只输出JSON，不要其他内容："""
