import { HTMLAttributes, forwardRef } from 'react';
import { cn } from '../utils/helpers';

export const Table = forwardRef<HTMLTableElement, HTMLAttributes<HTMLTableElement>>(
  ({ className, children, ...rest }, ref) => (
    <div className={cn('table-container', className)} {...rest}>
      <table className="table" ref={ref}>
        {children}
      </table>
    </div>
  )
);

Table.displayName = 'Table';

export const TableHeader = forwardRef<HTMLTableSectionElement, HTMLAttributes<HTMLTableSectionElement>>(
  ({ className, children, ...rest }, ref) => (
    <thead className={cn('[&_tr]:border-b-[1px]_border-dark-700', className)} ref={ref} {...rest}>
      {children}
    </thead>
  )
);

TableHeader.displayName = 'TableHeader';

export const TableBody = forwardRef<HTMLTableSectionElement, HTMLAttributes<HTMLTableSectionElement>>(
  ({ className, children, ...rest }, ref) => (
    <tbody className={cn('[&_tr:last-child]:border-0', className)} ref={ref} {...rest}>
      {children}
    </tbody>
  )
);

TableBody.displayName = 'TableBody';

export const TableRow = forwardRef<HTMLTableRowElement, HTMLAttributes<HTMLTableRowElement>>(
  ({ className, children, ...rest }, ref) => (
    <tr className={cn('hover:bg-dark-800/50 transition-colors', className)} ref={ref} {...rest}>
      {children}
    </tr>
  )
);

TableRow.displayName = 'TableRow';

export const TableHead = forwardRef<HTMLTableCellElement, HTMLAttributes<HTMLTableCellElement>>(
  ({ className, children, ...rest }, ref) => (
    <th className={cn('px-4 py-3 text-left font-medium text-dark-400 bg-dark-900 uppercase tracking-wider', className)} ref={ref} {...rest}>
      {children}
    </th>
  )
);

TableHead.displayName = 'TableHead';

export const TableCell = forwardRef<HTMLTableCellElement, HTMLAttributes<HTMLTableCellElement>>(
  ({ className, children, ...rest }, ref) => (
    <td className={cn('px-4 py-3 border-b border-dark-800', className)} ref={ref} {...rest}>
      {children}
    </td>
  )
);

TableCell.displayName = 'TableCell';