import { useMemo, useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
} from '@tanstack/react-table';

//FUNCTION FOR TAKING A LIST HEADER AND A LIST OF LISTS DATA RETURNED BY GOOGLE SHEETS API AND MAKING IT INTO TANSTACK TABLES
export function useListTable({ rawColumns = [], rawData = [] }) {
  const [sorting, setSorting] = useState([]);

  // 1. Columns are created with a meaningful accessorKey (the header name)
  const columns = useMemo(() => {
    return rawColumns.map(header => ({
      header: header,
      accessorKey: header, // Use the name, e.g., 'Name', 'Age'
    }));
  }, [rawColumns]);

  // 2. THIS IS THE CRUCIAL PART: Data is transformed into objects
  const data = useMemo(() => {
    // Transforms [['John', 30]] into [{ Name: 'John', Age: 30 }]
    return rawData.map(rowArray => {
      const rowObject = {};
      rawColumns.forEach((header, index) => {
        rowObject[header] = rowArray[index];
      });
      return rowObject;
    });
  }, [rawData, rawColumns]);

  const table = useReactTable({
    data, // Now passing a list of objects
    columns, // Now using named keys
    state: {
      sorting,
    },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return table;
}