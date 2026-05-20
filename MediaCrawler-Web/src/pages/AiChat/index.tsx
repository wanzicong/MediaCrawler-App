import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Input, Button, Card, Space, Spin, message, Tag, Avatar,
  Dropdown, Modal, Drawer, List, Typography, Popconfirm, Empty, Badge,
} from 'antd';
import {
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  ClearOutlined,
  ThunderboltOutlined,
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  MoreOutlined,
  HistoryOutlined,
  StarOutlined,
  MenuOutlined,
} from '@ant-design/icons';
import {
  sendChatMessage,
  fetchSessions,
  createSession,
  deleteSession,
  renameSession,
  fetchSessionMessages,
  fetchMemories,
  createMemory,
  deleteMemory,
  type ChatMessage,
  type SessionInfo,
  type MemoryInfo,
} from '@/api/modules/ai';
import styles from './index.module.less';

const { TextArea } = Input;
const { Text, Paragraph } = Typography;

const WELCOME_MESSAGE: ChatMessage = {
  role: 'assistant',
  content: '你好！我是 DeepSeek AI 助手。选择一个会话或创建新对话开始聊天。',
};

export default function AiChatPage() {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [memories, setMemories] = useState<MemoryInfo[]>([]);
  const [memoryDrawerOpen, setMemoryDrawerOpen] = useState(false);
  const [sessionDrawerOpen, setSessionDrawerOpen] = useState(false);
  const [editingSession, setEditingSession] = useState<SessionInfo | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [newMemoryKey, setNewMemoryKey] = useState('');
  const [newMemoryContent, setNewMemoryContent] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // 加载会话列表
  const loadSessions = useCallback(async () => {
    try {
      const list = await fetchSessions();
      setSessions(list);
      return list;
    } catch {
      message.error('加载会话列表失败');
      return [];
    }
  }, []);

  // 加载记忆列表
  const loadMemories = useCallback(async () => {
    try {
      const list = await fetchMemories();
      setMemories(list);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadSessions();
    loadMemories();
  }, [loadSessions, loadMemories]);

  // 切换会话
  const handleSelectSession = async (sessionId: number) => {
    setActiveSessionId(sessionId);
    try {
      const resp = await fetchSessionMessages(sessionId);
      if (resp.messages && resp.messages.length > 0) {
        setMessages(resp.messages);
      } else {
        setMessages([{ role: 'assistant', content: '开始新的对话吧！' }]);
      }
    } catch {
      setMessages([WELCOME_MESSAGE]);
    }
    setSessionDrawerOpen(false);
  };

  // 新建会话
  const handleNewSession = async (title?: string) => {
    try {
      const session = await createSession(title || '新对话');
      await loadSessions();
      setActiveSessionId(session.id);
      setMessages([{ role: 'assistant', content: '开始新的对话吧！' }]);
      setSessionDrawerOpen(false);
    } catch {
      message.error('创建会话失败');
    }
  };

  // 删除会话
  const handleDeleteSession = async (id: number) => {
    try {
      await deleteSession(id);
      message.success('会话已删除');
      if (activeSessionId === id) {
        setActiveSessionId(null);
        setMessages([WELCOME_MESSAGE]);
      }
      await loadSessions();
    } catch {
      message.error('删除会话失败');
    }
  };

  // 重命名会话
  const handleRenameStart = (session: SessionInfo) => {
    setEditingSession(session);
    setEditTitle(session.title);
  };
  const handleRenameConfirm = async () => {
    if (!editingSession) return;
    try {
      await renameSession(editingSession.id, editTitle);
      message.success('已重命名');
      setEditingSession(null);
      await loadSessions();
    } catch {
      message.error('重命名失败');
    }
  };

  // 过滤占位消息，只保留真实对话
  const PLACEHOLDER_CONTENTS = new Set([
    WELCOME_MESSAGE.content,
    '开始新的对话吧！',
  ]);
  const filterPlaceholders = (msgs: ChatMessage[]) =>
    msgs.filter((m) => !PLACEHOLDER_CONTENTS.has(m.content));

  // 发送消息
  const handleSend = async () => {
    const text = inputValue.trim();
    if (!text || loading) return;

    const userMessage: ChatMessage = { role: 'user', content: text };
    const displayMessages = [...messages, userMessage];
    setMessages(displayMessages);
    setInputValue('');
    setLoading(true);

    try {
      const resp = await sendChatMessage({
        session_id: activeSessionId,
        messages: filterPlaceholders(displayMessages),
      });
      const assistantMessage: ChatMessage = { role: 'assistant', content: resp.content };
      setMessages((prev) => [...prev, assistantMessage]);

      // 如果是新会话（自动创建），更新 activeSessionId
      if (!activeSessionId) {
        setActiveSessionId(resp.session_id);
        await loadSessions();
      }
    } catch {
      message.error('AI 请求失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 清空当前会话消息（通过新建实现）
  const handleClear = () => {
    handleNewSession();
  };

  // 添加记忆
  const handleAddMemory = async () => {
    if (!newMemoryKey.trim() || !newMemoryContent.trim()) {
      message.warning('请填写记忆标识和内容');
      return;
    }
    try {
      await createMemory(newMemoryKey.trim(), newMemoryContent.trim());
      message.success('记忆已保存');
      setNewMemoryKey('');
      setNewMemoryContent('');
      await loadMemories();
    } catch {
      message.error('保存记忆失败');
    }
  };

  // 删除记忆
  const handleDeleteMemory = async (id: number) => {
    try {
      await deleteMemory(id);
      message.success('记忆已删除');
      await loadMemories();
    } catch {
      message.error('删除记忆失败');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  return (
    <div className={styles.container}>
      {/* 移动端会话抽屉 */}
      <Drawer
        title="会话列表"
        placement="left"
        open={sessionDrawerOpen}
        onClose={() => setSessionDrawerOpen(false)}
        width={280}
        extra={
          <Button
            type="primary"
            size="small"
            icon={<PlusOutlined />}
            onClick={() => handleNewSession()}
          >
            新建
          </Button>
        }
      >
        <SessionList
          sessions={sessions}
          activeId={activeSessionId}
          onSelect={handleSelectSession}
          onDelete={handleDeleteSession}
          onRename={handleRenameStart}
          editingSession={editingSession}
          editTitle={editTitle}
          onEditTitleChange={setEditTitle}
          onRenameConfirm={handleRenameConfirm}
          onEditCancel={() => setEditingSession(null)}
        />
      </Drawer>

      {/* 左侧会话列表（桌面端） */}
      <div className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <Button
            type="primary"
            block
            icon={<PlusOutlined />}
            onClick={() => handleNewSession()}
          >
            新建对话
          </Button>
        </div>
        <div className={styles.sidebarList}>
          <SessionList
            sessions={sessions}
            activeId={activeSessionId}
            onSelect={handleSelectSession}
            onDelete={handleDeleteSession}
            onRename={handleRenameStart}
            editingSession={editingSession}
            editTitle={editTitle}
            onEditTitleChange={setEditTitle}
            onRenameConfirm={handleRenameConfirm}
            onEditCancel={() => setEditingSession(null)}
          />
        </div>
      </div>

      {/* 主聊天区域 */}
      <div className={styles.chatArea}>
        <Card
          className={styles.chatCard}
          title={
            <Space>
              {/* 移动端菜单按钮 */}
              <Button
                className={styles.mobileMenuBtn}
                type="text"
                icon={<MenuOutlined />}
                onClick={() => setSessionDrawerOpen(true)}
              />
              <ThunderboltOutlined style={{ color: '#6366f1' }} />
              <span className={styles.chatTitle}>
                {activeSession?.title || 'DeepSeek AI 对话'}
              </span>
              {activeSession && (
                <Tag color="purple" style={{ marginLeft: 4 }}>
                  {messages.length} 条消息
                </Tag>
              )}
            </Space>
          }
          extra={
            <Space>
              <Button
                icon={<StarOutlined />}
                onClick={() => { setMemoryDrawerOpen(true); loadMemories(); }}
                size="small"
              >
                记忆管理
                {memories.length > 0 && (
                  <Badge count={memories.length} size="small" style={{ marginLeft: 4 }} />
                )}
              </Button>
              <Button
                icon={<ClearOutlined />}
                onClick={handleClear}
                disabled={loading}
                size="small"
              >
                新建
              </Button>
            </Space>
          }
        >
          <div className={styles.messageList}>
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`${styles.messageItem} ${
                  msg.role === 'user' ? styles.userMessage : styles.assistantMessage
                }`}
              >
                <div className={styles.avatar}>
                  {msg.role === 'user' ? (
                    <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#6366f1' }} />
                  ) : (
                    <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#10b981' }} />
                  )}
                </div>
                <div className={styles.messageContent}>
                  <div className={styles.roleLabel}>
                    {msg.role === 'user' ? '你' : 'DeepSeek'}
                  </div>
                  <div className={styles.bubble}>
                    {msg.content.split('\n').map((line, i) => (
                      <span key={i}>
                        {line}
                        {i < msg.content.split('\n').length - 1 && <br />}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
            {loading && (
              <div className={`${styles.messageItem} ${styles.assistantMessage}`}>
                <div className={styles.avatar}>
                  <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#10b981' }} />
                </div>
                <div className={styles.messageContent}>
                  <div className={styles.roleLabel}>DeepSeek</div>
                  <div className={styles.bubble}>
                    <Spin size="small" /> 思考中...
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className={styles.inputArea}>
            <TextArea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入你的问题，Enter 发送，Shift+Enter 换行"
              autoSize={{ minRows: 1, maxRows: 4 }}
              disabled={loading}
              className={styles.textArea}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              loading={loading}
              disabled={!inputValue.trim()}
              className={styles.sendBtn}
            >
              发送
            </Button>
          </div>
        </Card>
      </div>

      {/* 记忆管理抽屉 */}
      <Drawer
        title={
          <Space>
            <StarOutlined />
            记忆管理
            <Tag color="blue">{memories.length} 条</Tag>
          </Space>
        }
        placement="right"
        open={memoryDrawerOpen}
        onClose={() => setMemoryDrawerOpen(false)}
        width={420}
      >
        <div className={styles.memorySection}>
          <Card size="small" title="添加新记忆" style={{ marginBottom: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Input
                placeholder="记忆标识（如：我的职业）"
                value={newMemoryKey}
                onChange={(e) => setNewMemoryKey(e.target.value)}
              />
              <TextArea
                placeholder="记忆内容（如：我是一名后端开发工程师）"
                value={newMemoryContent}
                onChange={(e) => setNewMemoryContent(e.target.value)}
                autoSize={{ minRows: 2, maxRows: 4 }}
              />
              <Button type="primary" onClick={handleAddMemory} block>
                保存记忆
              </Button>
            </Space>
          </Card>

          <div className={styles.memoryListTitle}>
            <Text strong>已有记忆</Text>
          </div>
          {memories.length === 0 ? (
            <Empty description="暂无记忆，AI 将不会记住任何信息" />
          ) : (
            <List
              dataSource={memories}
              renderItem={(item) => (
                <List.Item
                  actions={[
                    <Popconfirm
                      key="delete"
                      title="确定删除这条记忆？"
                      onConfirm={() => handleDeleteMemory(item.id)}
                    >
                      <Button type="text" danger icon={<DeleteOutlined />} size="small" />
                    </Popconfirm>,
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <Space>
                        <Tag color="geekblue">{item.category}</Tag>
                        <Text strong>{item.key}</Text>
                      </Space>
                    }
                    description={item.content}
                  />
                </List.Item>
              )}
            />
          )}
        </div>
        <div className={styles.memoryTip}>
          <Text type="secondary">
            记忆会在 AI 对话时自动注入到系统提示中，帮助 AI 更好地了解你。
          </Text>
        </div>
      </Drawer>

      {/* 重命名 Modal */}
      <Modal
        title="重命名会话"
        open={!!editingSession}
        onOk={handleRenameConfirm}
        onCancel={() => setEditingSession(null)}
        okText="确定"
        cancelText="取消"
      >
        <Input
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          placeholder="输入新标题"
          onPressEnter={handleRenameConfirm}
        />
      </Modal>
    </div>
  );
}

// ── 会话列表子组件 ────────────────────────────────────────────────

function SessionList({
  sessions,
  activeId,
  onSelect,
  onDelete,
  onRename,
  editingSession,
  editTitle,
  onEditTitleChange,
  onRenameConfirm,
  onEditCancel,
}: {
  sessions: SessionInfo[];
  activeId: number | null;
  onSelect: (id: number) => void;
  onDelete: (id: number) => void;
  onRename: (s: SessionInfo) => void;
  editingSession: SessionInfo | null;
  editTitle: string;
  onEditTitleChange: (v: string) => void;
  onRenameConfirm: () => void;
  onEditCancel: () => void;
}) {
  if (sessions.length === 0) {
    return <Empty description="暂无会话" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  return (
    <List
      dataSource={sessions}
      renderItem={(item) => (
        <List.Item
          key={item.id}
          className={`${styles.sessionItem} ${item.id === activeId ? styles.sessionActive : ''}`}
          onClick={() => {
            if (editingSession?.id === item.id) return;
            onSelect(item.id);
          }}
          actions={[
            <Dropdown
              key="more"
              menu={{
                items: [
                  {
                    key: 'rename',
                    icon: <EditOutlined />,
                    label: '重命名',
                    onClick: (e: any) => {
                      e.domEvent.stopPropagation();
                      onRename(item);
                    },
                  },
                  {
                    key: 'delete',
                    icon: <DeleteOutlined />,
                    label: '删除',
                    danger: true,
                    onClick: (e: any) => {
                      e.domEvent.stopPropagation();
                      onDelete(item.id);
                    },
                  },
                ],
              }}
              trigger={['click']}
            >
              <Button
                type="text"
                size="small"
                icon={<MoreOutlined />}
                onClick={(e) => e.stopPropagation()}
              />
            </Dropdown>,
          ]}
        >
          <List.Item.Meta
            avatar={<HistoryOutlined style={{ color: item.id === activeId ? '#6366f1' : '#999' }} />}
            title={
              editingSession?.id === item.id ? (
                <Input
                  size="small"
                  value={editTitle}
                  onChange={(e) => onEditTitleChange(e.target.value)}
                  onPressEnter={onRenameConfirm}
                  onBlur={onEditCancel}
                  onClick={(e) => e.stopPropagation()}
                  autoFocus
                />
              ) : (
                <Text
                  ellipsis
                  style={{ maxWidth: 160, fontWeight: item.id === activeId ? 600 : 400 }}
                >
                  {item.title}
                </Text>
              )
            }
            description={
              <Text type="secondary" style={{ fontSize: 12 }}>
                {item.message_count} 条消息
              </Text>
            }
          />
        </List.Item>
      )}
    />
  );
}
