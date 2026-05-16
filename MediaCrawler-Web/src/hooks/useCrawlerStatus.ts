import { useQuery } from '@tanstack/react-query';

import { fetchCrawlerStatus } from '@/api';

export function useCrawlerStatus(polling = false) {
  return useQuery({
    queryKey: ['crawler', 'status'],
    queryFn: fetchCrawlerStatus,
    refetchInterval: polling ? 3000 : false,
  });
}
