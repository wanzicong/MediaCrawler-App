import { Card, Col, Row, Statistic, Tag, Typography, List } from 'antd';
import { SmileOutlined, MehOutlined, FrownOutlined, BulbOutlined, FireOutlined } from '@ant-design/icons';
import type { AnalyzeResponse } from '@/api/modules/ai';

const { Text, Title, Paragraph } = Typography;

const SENTIMENT_COLORS = {
  positive: '#10b981',
  neutral: '#f59e0b',
  negative: '#ef4444',
};

export default function AnalysisResultCard({ result }: { result: AnalyzeResponse }) {
  const { sentiment, key_insights, summary, hot_topics, comment_count, platform } = result;

  return (
    <div style={{ padding: '8px 0' }}>
      {/* 情感分析 */}
      <Card size="small" title="情感分布" style={{ marginBottom: 16 }}>
        <Row gutter={24} justify="center">
          <Col span={8} style={{ textAlign: 'center' }}>
            <Statistic
              title="正面"
              value={sentiment.positive}
              suffix="%"
              prefix={<SmileOutlined style={{ color: SENTIMENT_COLORS.positive }} />}
              valueStyle={{ color: SENTIMENT_COLORS.positive }}
            />
          </Col>
          <Col span={8} style={{ textAlign: 'center' }}>
            <Statistic
              title="中性"
              value={sentiment.neutral}
              suffix="%"
              prefix={<MehOutlined style={{ color: SENTIMENT_COLORS.neutral }} />}
              valueStyle={{ color: SENTIMENT_COLORS.neutral }}
            />
          </Col>
          <Col span={8} style={{ textAlign: 'center' }}>
            <Statistic
              title="负面"
              value={sentiment.negative}
              suffix="%"
              prefix={<FrownOutlined style={{ color: SENTIMENT_COLORS.negative }} />}
              valueStyle={{ color: SENTIMENT_COLORS.negative }}
            />
          </Col>
        </Row>
        <div style={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden', marginTop: 16 }}>
          <div style={{ width: `${sentiment.positive}%`, background: SENTIMENT_COLORS.positive, transition: 'width 0.3s' }} />
          <div style={{ width: `${sentiment.neutral}%`, background: SENTIMENT_COLORS.neutral, transition: 'width 0.3s' }} />
          <div style={{ width: `${sentiment.negative}%`, background: SENTIMENT_COLORS.negative, transition: 'width 0.3s' }} />
        </div>
        <Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0 }}>
          {sentiment.summary}
        </Paragraph>
      </Card>

      {/* 综合摘要 */}
      <Card size="small" title="综合摘要" style={{ marginBottom: 16 }}>
        <Paragraph>{summary}</Paragraph>
      </Card>

      {/* 关键观点 */}
      {key_insights.length > 0 && (
        <Card
          size="small"
          title={<><BulbOutlined /> 关键观点</>}
          style={{ marginBottom: 16 }}
        >
          <List
            dataSource={key_insights}
            renderItem={(item, idx) => (
              <List.Item>
                <div>
                  <Text strong>{idx + 1}. {item.point}</Text>
                  <br />
                  <Text type="secondary" italic>&ldquo;{item.representative_comment}&rdquo;</Text>
                </div>
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* 热点话题 */}
      {hot_topics.length > 0 && (
        <Card size="small" title={<><FireOutlined /> 热点话题</>}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {hot_topics.map((topic, idx) => (
              <Tag key={idx} color="magenta" style={{ fontSize: 14, padding: '4px 12px' }}>
                #{topic}
              </Tag>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
