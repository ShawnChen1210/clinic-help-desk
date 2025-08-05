import { useMemo, useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
} from '@tanstack/react-table';

//INFO: function for columns from pandas dataframe's df.columns.to_list and data from df.to_dict to make a tanstack table object
export function useDictTable({ rawColumns = [], rawData = [] }) {
  const [sorting, setSorting] = useState([]);

  // Improvement: Wrapped in useMemo for performance
  const columns = useMemo(() => {
    return rawColumns.map(header => ({
      header: header,
      accessorKey: header,
    }));
  }, [rawColumns]);

  const data = useMemo(() => rawData, [rawData]);

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
    },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  // CRITICAL FIX: Return the table instance
  return table;
}