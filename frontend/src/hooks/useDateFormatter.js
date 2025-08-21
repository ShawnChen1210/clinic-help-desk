import { useCallback } from 'react';

export const useDateFormatter = () => {
  const formatDateString = useCallback((dateString) => {
    if (typeof dateString === 'string' && dateString.match(/^\d{4}-\d{2}-\d{2}$/)) {
      const [year, month, day] = dateString.split('-');
      const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
      return date.toLocaleDateString();
    }
    return new Date(dateString).toLocaleDateString();
  }, []);

  return { formatDateString };
};