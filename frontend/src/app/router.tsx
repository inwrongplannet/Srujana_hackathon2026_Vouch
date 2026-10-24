import { createBrowserRouter, Navigate } from 'react-router';
import { AppShell } from '@/layout/AppShell';
import { OnboardingPage } from '@/routes/OnboardingPage';
import { BorrowerPage } from '@/routes/BorrowerPage';
import { VoucherPage } from '@/routes/VoucherPage';
import { LenderPage } from '@/routes/LenderPage';
import { ApplicantPage } from '@/routes/ApplicantPage';

export const router = createBrowserRouter([
  { path: '/', element: <Navigate to="/login" replace /> },
  { path: '/login', element: <OnboardingPage /> },
  {
    path: '/app',
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="borrower" replace /> },
      { path: 'borrower', element: <BorrowerPage /> },
      { path: 'voucher', element: <VoucherPage /> },
      { path: 'lender', element: <LenderPage /> },
      { path: 'lender/:nodeId', element: <ApplicantPage /> },
    ],
  },
  { path: '*', element: <Navigate to="/login" replace /> },
]);
