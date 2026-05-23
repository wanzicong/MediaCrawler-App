/** 每个平台+类型只展示的核心字段 */
export const IMPORTANT_FIELDS: Record<string, string[]> = {
  // 笔记列表：头像、昵称、标题、封面
  'xhs.contents': ['avatar', 'nickname', 'title', 'image_list'],
  'wb.contents': ['avatar', 'nickname', 'content'],
  'tieba.contents': ['user_avatar', 'user_nickname', 'title'],
  'zhihu.contents': ['user_avatar', 'user_nickname', 'title'],

  // 视频列表：头像、昵称、标题、视频封面
  'dy.contents': ['avatar', 'nickname', 'title', 'cover_url'],
  'ks.contents': ['avatar', 'nickname', 'title', 'video_cover_url'],
  'bili.contents': ['avatar', 'nickname', 'title', 'video_cover_url', 'video_url', 'video_play_count', 'video_comment', 'liked_count'],

  // 评论：头像、昵称、内容、创建时间
  'xhs.comments': ['avatar', 'nickname', 'content', 'create_time'],
  'dy.comments': ['avatar', 'nickname', 'content', 'create_time'],
  'ks.comments': ['avatar', 'nickname', 'content', 'create_time'],
  'bili.comments': ['avatar', 'nickname', 'content', 'create_time'],
  'wb.comments': ['avatar', 'nickname', 'content', 'create_time'],
  'tieba.comments': ['user_avatar', 'user_nickname', 'content', 'publish_time'],
  'zhihu.comments': ['user_avatar', 'user_nickname', 'content', 'publish_time'],

  // 创作者（保持不变）
  'xhs.creators': ['user_id', 'nickname', 'avatar', 'desc', 'gender', 'follows', 'fans', 'interaction', 'ip_location'],
};

/** 字段名 → 中文标签 */
export const FIELD_LABELS: Record<string, string> = {
  id: 'ID', note_id: '笔记ID', video_id: '视频ID', aweme_id: '作品ID', comment_id: '评论ID', content_id: '内容ID',
  user_id: '用户ID', sec_uid: '安全UID', short_user_id: '短UID', user_unique_id: '用户唯一ID', user_link: '用户链接',
  nickname: '昵称', user_nickname: '昵称', user_name: '用户名', avatar: '头像', user_avatar: '头像',
  title: '标题', desc: '描述', content: '内容', content_text: '内容文本', type: '类型', content_type: '内容类型',
  time: '时间', create_time: '创建时间', created_time: '创建时间', publish_time: '发布时间', pub_ts: '发布时间',
  create_date_time: '创建日期', last_update_time: '最后更新', updated_time: '更新时间',
  add_ts: '添加时间戳', last_modify_ts: '最后修改时间戳',
  liked_count: '点赞', comment_count: '评论', collected_count: '收藏', share_count: '分享', shared_count: '分享',
  viewd_count: '播放', video_play_count: '播放', video_favorite_count: '收藏', video_share_count: '分享',
  video_comment: '评论', video_danmaku: '弹幕', video_coin_count: '硬币', disliked_count: '点踩',
  voteup_count: '赞同', like_count: '点赞', comment_like_count: '评论点赞', total_liked: '总获赞',
  sub_comment_count: '子评论', total_replay_num: '总回复', total_replay_page: '总回复页',
  follows: '关注', fans: '粉丝', interaction: '互动', videos_count: '视频数',
  note_url: '链接', video_url: '链接', aweme_url: '链接', content_url: '链接', note_download_url: '笔记下载',
  video_download_url: '视频下载', music_download_url: '音乐下载', video_play_url: '播放链接',
  cover_url: '封面', video_cover_url: '封面', image_list: '图片列表', pictures: '图片',
  tag_list: '标签', source_keyword: '来源关键词', xsec_token: 'XsecToken',
  ip_location: 'IP属地', gender: '性别', sex: '性别', sign: '签名', user_signature: '签名',
  aweme_type: '作品类型', video_type: '视频类型',
  parent_comment_id: '父评论ID', tieba_name: '贴吧', tieba_id: '贴吧ID', tieba_link: '贴吧链接',
  profile_url: '主页', anwser_count: '回答', video_count: '视频数', question_count: '问题', article_count: '文章',
  column_count: '专栏', get_voteup_count: '获赞', user_url_token: 'URLToken', url_token: 'URLToken',
  registration_duration: '注册时长', is_official: '是否认证', user_rank: '用户等级', total_fans: '总粉丝',
  question_id: '问题ID',
};

/** 时间戳字段 */
export const TS_FIELDS: ReadonlySet<string> = new Set([
  'time', 'create_time', 'created_time', 'publish_time', 'pub_ts', 'last_update_time', 'updated_time',
  'add_ts', 'last_modify_ts',
]);

/** 头像/封面字段 */
export const IMAGE_FIELDS: ReadonlySet<string> = new Set([
  'avatar', 'user_avatar', 'cover_url', 'video_cover_url', 'image_list',
]);
