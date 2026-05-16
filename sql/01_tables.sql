-- Auto-generated from SQLAlchemy models
USE media_crawler;

CREATE TABLE bilibili_contact_info (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	up_id BIGINT COMMENT 'UP主ID', 
	fan_id BIGINT COMMENT '粉丝ID', 
	up_name TEXT COMMENT 'UP主名称', 
	fan_name TEXT COMMENT '粉丝名称', 
	up_sign TEXT COMMENT 'UP主签名', 
	fan_sign TEXT COMMENT '粉丝签名', 
	up_avatar TEXT COMMENT 'UP主头像', 
	fan_avatar TEXT COMMENT '粉丝头像', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	PRIMARY KEY (id)
);

CREATE TABLE bilibili_up_dynamic (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	dynamic_id BIGINT COMMENT '动态ID', 
	user_id VARCHAR(255) COMMENT '用户ID', 
	user_name TEXT COMMENT '用户名称', 
	text TEXT COMMENT '动态内容', 
	type TEXT COMMENT '动态类型', 
	pub_ts BIGINT COMMENT '发布时间戳', 
	total_comments INTEGER COMMENT '总评论数', 
	total_forwards INTEGER COMMENT '总转发数', 
	total_liked INTEGER COMMENT '总点赞数', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	PRIMARY KEY (id)
);

CREATE TABLE bilibili_up_info (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	user_id BIGINT COMMENT '用户ID', 
	nickname TEXT COMMENT '用户昵称', 
	sex TEXT COMMENT '性别', 
	sign TEXT COMMENT '签名', 
	avatar TEXT COMMENT '头像', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	total_fans INTEGER COMMENT '总粉丝数', 
	total_liked INTEGER COMMENT '总获赞数', 
	user_rank INTEGER COMMENT '用户等级', 
	is_official INTEGER COMMENT '是否官方认证', 
	PRIMARY KEY (id)
);

CREATE TABLE bilibili_video (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	video_id BIGINT NOT NULL COMMENT '视频ID', 
	video_url TEXT NOT NULL COMMENT '视频URL', 
	user_id BIGINT COMMENT '用户ID', 
	nickname TEXT COMMENT '用户昵称', 
	avatar TEXT COMMENT '用户头像', 
	liked_count INTEGER COMMENT '点赞数', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	video_type TEXT COMMENT '视频类型', 
	title TEXT COMMENT '视频标题', 
	`desc` TEXT COMMENT '视频描述', 
	create_time BIGINT COMMENT '创建时间戳', 
	disliked_count TEXT COMMENT '点踩数', 
	video_play_count TEXT COMMENT '播放数', 
	video_favorite_count TEXT COMMENT '收藏数', 
	video_share_count TEXT COMMENT '分享数', 
	video_coin_count TEXT COMMENT '硬币数', 
	video_danmaku TEXT COMMENT '弹幕数', 
	video_comment TEXT COMMENT '评论数', 
	video_cover_url TEXT COMMENT '视频封面URL', 
	source_keyword TEXT COMMENT '来源关键词', 
	PRIMARY KEY (id)
);

CREATE TABLE bilibili_video_comment (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	user_id VARCHAR(255) COMMENT '用户ID', 
	nickname TEXT COMMENT '用户昵称', 
	sex TEXT COMMENT '性别', 
	sign TEXT COMMENT '签名', 
	avatar TEXT COMMENT '头像', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	comment_id BIGINT COMMENT '评论ID', 
	video_id BIGINT COMMENT '视频ID', 
	content TEXT COMMENT '评论内容', 
	create_time BIGINT COMMENT '创建时间戳', 
	sub_comment_count TEXT COMMENT '子评论数', 
	parent_comment_id VARCHAR(255) COMMENT '父评论ID', 
	like_count TEXT COMMENT '点赞数', 
	PRIMARY KEY (id)
);

CREATE TABLE crawler_profile (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(128) NOT NULL COMMENT '方案名称', 
	description TEXT COMMENT '说明', 
	is_default BOOL COMMENT '是否默认方案', 
	payload JSON NOT NULL COMMENT '完整配置 JSON', 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE crawler_task (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	profile_id INTEGER COMMENT '来源方案 ID', 
	status VARCHAR(32) COMMENT 'pending|running|completed|failed|cancelled', 
	payload_snapshot JSON NOT NULL COMMENT '启动时配置快照', 
	error_message TEXT, 
	created_at DATETIME, 
	started_at DATETIME, 
	finished_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE TABLE douyin_aweme (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	user_id VARCHAR(255) COMMENT '用户ID', 
	sec_uid VARCHAR(255) COMMENT '安全用户ID', 
	short_user_id VARCHAR(255) COMMENT '短用户ID', 
	user_unique_id VARCHAR(255) COMMENT '用户唯一ID', 
	nickname TEXT COMMENT '用户昵称', 
	avatar TEXT COMMENT '用户头像', 
	user_signature TEXT COMMENT '用户签名', 
	ip_location TEXT COMMENT 'IP地址位置', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	aweme_id BIGINT COMMENT '作品ID', 
	aweme_type TEXT COMMENT '作品类型', 
	title TEXT COMMENT '作品标题', 
	`desc` TEXT COMMENT '作品描述', 
	create_time BIGINT COMMENT '创建时间戳', 
	liked_count TEXT COMMENT '点赞数', 
	comment_count TEXT COMMENT '评论数', 
	share_count TEXT COMMENT '分享数', 
	collected_count TEXT COMMENT '收藏数', 
	aweme_url TEXT COMMENT '作品URL', 
	cover_url TEXT COMMENT '封面URL', 
	video_download_url TEXT COMMENT '视频下载URL', 
	music_download_url TEXT COMMENT '音乐下载URL', 
	note_download_url TEXT COMMENT '笔记下载URL', 
	source_keyword TEXT COMMENT '来源关键词', 
	PRIMARY KEY (id)
);

CREATE TABLE douyin_aweme_comment (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	user_id VARCHAR(255) COMMENT '用户ID', 
	sec_uid VARCHAR(255) COMMENT '安全用户ID', 
	short_user_id VARCHAR(255) COMMENT '短用户ID', 
	user_unique_id VARCHAR(255) COMMENT '用户唯一ID', 
	nickname TEXT COMMENT '用户昵称', 
	avatar TEXT COMMENT '用户头像', 
	user_signature TEXT COMMENT '用户签名', 
	ip_location TEXT COMMENT 'IP地址位置', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	comment_id BIGINT COMMENT '评论ID', 
	aweme_id BIGINT COMMENT '作品ID', 
	content TEXT COMMENT '评论内容', 
	create_time BIGINT COMMENT '创建时间戳', 
	sub_comment_count TEXT COMMENT '子评论数', 
	parent_comment_id VARCHAR(255) COMMENT '父评论ID', 
	like_count TEXT COMMENT '点赞数', 
	pictures TEXT COMMENT '图片', 
	PRIMARY KEY (id)
);

CREATE TABLE dy_creator (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	user_id VARCHAR(255) COMMENT '用户ID', 
	nickname TEXT COMMENT '用户昵称', 
	avatar TEXT COMMENT '用户头像', 
	ip_location TEXT COMMENT 'IP地址位置', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	`desc` TEXT COMMENT '描述', 
	gender TEXT COMMENT '性别', 
	follows TEXT COMMENT '关注数', 
	fans TEXT COMMENT '粉丝数', 
	interaction TEXT COMMENT '互动数', 
	videos_count VARCHAR(255) COMMENT '视频数量', 
	PRIMARY KEY (id)
);

CREATE TABLE kuaishou_video (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	user_id VARCHAR(64) COMMENT '用户ID', 
	nickname TEXT COMMENT '用户昵称', 
	avatar TEXT COMMENT '用户头像', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	video_id VARCHAR(255) COMMENT '视频ID', 
	video_type TEXT COMMENT '视频类型', 
	title TEXT COMMENT '视频标题', 
	`desc` TEXT COMMENT '视频描述', 
	create_time BIGINT COMMENT '创建时间戳', 
	liked_count TEXT COMMENT '点赞数', 
	viewd_count TEXT COMMENT '观看数', 
	video_url TEXT COMMENT '视频URL', 
	video_cover_url TEXT COMMENT '视频封面URL', 
	video_play_url TEXT COMMENT '视频播放URL', 
	source_keyword TEXT COMMENT '来源关键词', 
	PRIMARY KEY (id)
);

CREATE TABLE kuaishou_video_comment (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	user_id TEXT COMMENT '用户ID', 
	nickname TEXT COMMENT '用户昵称', 
	avatar TEXT COMMENT '用户头像', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	comment_id BIGINT COMMENT '评论ID', 
	video_id VARCHAR(255) COMMENT '视频ID', 
	content TEXT COMMENT '评论内容', 
	create_time BIGINT COMMENT '创建时间戳', 
	sub_comment_count TEXT COMMENT '子评论数', 
	PRIMARY KEY (id)
);

CREATE TABLE tieba_comment (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	comment_id VARCHAR(255) COMMENT '评论ID', 
	parent_comment_id VARCHAR(255) COMMENT '父评论ID', 
	content TEXT COMMENT '评论内容', 
	user_link TEXT COMMENT '用户链接', 
	user_nickname TEXT COMMENT '用户昵称', 
	user_avatar TEXT COMMENT '用户头像', 
	tieba_id VARCHAR(255) COMMENT '贴吧ID', 
	tieba_name TEXT COMMENT '贴吧名称', 
	tieba_link TEXT COMMENT '贴吧链接', 
	publish_time VARCHAR(255) COMMENT '发布时间', 
	ip_location TEXT COMMENT 'IP地址位置', 
	sub_comment_count INTEGER COMMENT '子评论数', 
	note_id VARCHAR(255) COMMENT '笔记ID', 
	note_url TEXT COMMENT '笔记URL', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	PRIMARY KEY (id)
);

CREATE TABLE tieba_creator (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	user_id VARCHAR(64) COMMENT '用户ID', 
	user_name TEXT COMMENT '用户名', 
	nickname TEXT COMMENT '用户昵称', 
	avatar TEXT COMMENT '用户头像', 
	ip_location TEXT COMMENT 'IP地址位置', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	gender TEXT COMMENT '性别', 
	follows TEXT COMMENT '关注数', 
	fans TEXT COMMENT '粉丝数', 
	registration_duration TEXT COMMENT '注册时长', 
	PRIMARY KEY (id)
);

CREATE TABLE tieba_note (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	note_id VARCHAR(644) COMMENT '笔记ID', 
	title TEXT COMMENT '笔记标题', 
	`desc` TEXT COMMENT '笔记描述', 
	note_url TEXT COMMENT '笔记URL', 
	publish_time VARCHAR(255) COMMENT '发布时间', 
	user_link TEXT COMMENT '用户链接', 
	user_nickname TEXT COMMENT '用户昵称', 
	user_avatar TEXT COMMENT '用户头像', 
	tieba_id VARCHAR(255) COMMENT '贴吧ID', 
	tieba_name TEXT COMMENT '贴吧名称', 
	tieba_link TEXT COMMENT '贴吧链接', 
	total_replay_num INTEGER COMMENT '总回复数', 
	total_replay_page INTEGER COMMENT '总回复页数', 
	ip_location TEXT COMMENT 'IP地址位置', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	source_keyword TEXT COMMENT '来源关键词', 
	PRIMARY KEY (id)
);

CREATE TABLE weibo_creator (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	user_id VARCHAR(255) COMMENT '用户ID', 
	nickname TEXT COMMENT '用户昵称', 
	avatar TEXT COMMENT '用户头像', 
	ip_location TEXT COMMENT 'IP地址位置', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	`desc` TEXT COMMENT '描述', 
	gender TEXT COMMENT '性别', 
	follows TEXT COMMENT '关注数', 
	fans TEXT COMMENT '粉丝数', 
	tag_list TEXT COMMENT '标签列表', 
	PRIMARY KEY (id)
);

CREATE TABLE weibo_note (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	user_id VARCHAR(255) COMMENT '用户ID', 
	nickname TEXT COMMENT '用户昵称', 
	avatar TEXT COMMENT '用户头像', 
	gender TEXT COMMENT '性别', 
	profile_url TEXT COMMENT '个人主页URL', 
	ip_location TEXT COMMENT 'IP地址位置', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	note_id BIGINT COMMENT '笔记ID', 
	content TEXT COMMENT '笔记内容', 
	create_time BIGINT COMMENT '创建时间戳', 
	create_date_time VARCHAR(255) COMMENT '创建日期时间', 
	liked_count TEXT COMMENT '点赞数', 
	comments_count TEXT COMMENT '评论数', 
	shared_count TEXT COMMENT '分享数', 
	note_url TEXT COMMENT '笔记URL', 
	source_keyword TEXT COMMENT '来源关键词', 
	PRIMARY KEY (id)
);

CREATE TABLE weibo_note_comment (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	user_id VARCHAR(255) COMMENT '用户ID', 
	nickname TEXT COMMENT '用户昵称', 
	avatar TEXT COMMENT '用户头像', 
	gender TEXT COMMENT '性别', 
	profile_url TEXT COMMENT '个人主页URL', 
	ip_location TEXT COMMENT 'IP地址位置', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	comment_id BIGINT COMMENT '评论ID', 
	note_id BIGINT COMMENT '笔记ID', 
	content TEXT COMMENT '评论内容', 
	create_time BIGINT COMMENT '创建时间戳', 
	create_date_time VARCHAR(255) COMMENT '创建日期时间', 
	comment_like_count TEXT COMMENT '评论点赞数', 
	sub_comment_count TEXT COMMENT '子评论数', 
	parent_comment_id VARCHAR(255) COMMENT '父评论ID', 
	PRIMARY KEY (id)
);

CREATE TABLE xhs_creator (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	user_id VARCHAR(255) COMMENT '用户ID', 
	nickname TEXT COMMENT '用户昵称', 
	avatar TEXT COMMENT '用户头像', 
	ip_location TEXT COMMENT 'IP地址位置', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	`desc` TEXT COMMENT '描述', 
	gender TEXT COMMENT '性别', 
	follows TEXT COMMENT '关注数', 
	fans TEXT COMMENT '粉丝数', 
	interaction TEXT COMMENT '互动数', 
	tag_list TEXT COMMENT '标签列表', 
	PRIMARY KEY (id)
);

CREATE TABLE xhs_note (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	user_id VARCHAR(255) COMMENT '用户ID', 
	nickname TEXT COMMENT '用户昵称', 
	avatar TEXT COMMENT '用户头像', 
	ip_location TEXT COMMENT 'IP地址位置', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	note_id VARCHAR(255) COMMENT '笔记ID', 
	type TEXT COMMENT '笔记类型', 
	title TEXT COMMENT '笔记标题', 
	`desc` TEXT COMMENT '笔记描述', 
	video_url TEXT COMMENT '视频URL', 
	time BIGINT COMMENT '时间戳', 
	last_update_time BIGINT COMMENT '最后更新时间戳', 
	liked_count TEXT COMMENT '点赞数', 
	collected_count TEXT COMMENT '收藏数', 
	comment_count TEXT COMMENT '评论数', 
	share_count TEXT COMMENT '分享数', 
	image_list TEXT COMMENT '图片列表', 
	tag_list TEXT COMMENT '标签列表', 
	note_url TEXT COMMENT '笔记URL', 
	source_keyword TEXT COMMENT '来源关键词', 
	xsec_token TEXT COMMENT 'Xsec Token', 
	PRIMARY KEY (id)
);

CREATE TABLE xhs_note_comment (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	user_id VARCHAR(255) COMMENT '用户ID', 
	nickname TEXT COMMENT '用户昵称', 
	avatar TEXT COMMENT '用户头像', 
	ip_location TEXT COMMENT 'IP地址位置', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	comment_id VARCHAR(255) COMMENT '评论ID', 
	create_time BIGINT COMMENT '创建时间戳', 
	note_id VARCHAR(255) COMMENT '笔记ID', 
	content TEXT COMMENT '评论内容', 
	sub_comment_count INTEGER COMMENT '子评论数', 
	pictures TEXT COMMENT '图片', 
	parent_comment_id VARCHAR(255) COMMENT '父评论ID', 
	like_count TEXT COMMENT '点赞数', 
	PRIMARY KEY (id)
);

CREATE TABLE zhihu_comment (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	comment_id VARCHAR(64) COMMENT '评论ID', 
	parent_comment_id VARCHAR(64) COMMENT '父评论ID', 
	content TEXT COMMENT '评论内容', 
	publish_time VARCHAR(32) COMMENT '发布时间', 
	ip_location TEXT COMMENT 'IP地址位置', 
	sub_comment_count INTEGER COMMENT '子评论数', 
	like_count INTEGER COMMENT '点赞数', 
	dislike_count INTEGER COMMENT '点踩数', 
	content_id VARCHAR(64) COMMENT '内容ID', 
	content_type TEXT COMMENT '内容类型', 
	user_id VARCHAR(64) COMMENT '用户ID', 
	user_link TEXT COMMENT '用户链接', 
	user_nickname TEXT COMMENT '用户昵称', 
	user_avatar TEXT COMMENT '用户头像', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	PRIMARY KEY (id)
);

CREATE TABLE zhihu_content (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	content_id VARCHAR(64) COMMENT '内容ID', 
	content_type TEXT COMMENT '内容类型', 
	content_text TEXT COMMENT '内容文本', 
	content_url TEXT COMMENT '内容URL', 
	question_id VARCHAR(255) COMMENT '问题ID', 
	title TEXT COMMENT '标题', 
	`desc` TEXT COMMENT '描述', 
	created_time VARCHAR(32) COMMENT '创建时间', 
	updated_time TEXT COMMENT '更新时间', 
	voteup_count INTEGER COMMENT '赞同数', 
	comment_count INTEGER COMMENT '评论数', 
	source_keyword TEXT COMMENT '来源关键词', 
	user_id VARCHAR(255) COMMENT '用户ID', 
	user_link TEXT COMMENT '用户链接', 
	user_nickname TEXT COMMENT '用户昵称', 
	user_avatar TEXT COMMENT '用户头像', 
	user_url_token TEXT COMMENT '用户URL Token', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	PRIMARY KEY (id)
);

CREATE TABLE zhihu_creator (
	id INTEGER NOT NULL COMMENT '主键ID' AUTO_INCREMENT, 
	user_id VARCHAR(64) COMMENT '用户ID', 
	user_link TEXT COMMENT '用户链接', 
	user_nickname TEXT COMMENT '用户昵称', 
	user_avatar TEXT COMMENT '用户头像', 
	url_token TEXT COMMENT 'URL Token', 
	gender TEXT COMMENT '性别', 
	ip_location TEXT COMMENT 'IP地址位置', 
	follows INTEGER COMMENT '关注数', 
	fans INTEGER COMMENT '粉丝数', 
	anwser_count INTEGER COMMENT '回答数', 
	video_count INTEGER COMMENT '视频数', 
	question_count INTEGER COMMENT '问题数', 
	article_count INTEGER COMMENT '文章数', 
	column_count INTEGER COMMENT '专栏数', 
	get_voteup_count INTEGER COMMENT '获赞数', 
	add_ts BIGINT COMMENT '添加时间戳', 
	last_modify_ts BIGINT COMMENT '最后修改时间戳', 
	PRIMARY KEY (id)
);
