import { createBrowserRouter, Navigate } from 'react-router';
import { AppShell } from '@/layout/AppShell';
import { OnboardingPage } from '@/routes/OnboardingPage';
import { BorrowerPage } from '@/routes/BorrowerPage';
import { VoucherPage } from '@/routes/VoucherPage';
import { LenderPage } from '@/routes/LenderPage';
import { ApplicantPage } from '@/routes/ApplicantPage';
import { AssessPage } from '@/routes/AssessPage';
import { LandingPage } from '@/routes/LandingPage';
import { CommunityShell } from '@/layout/CommunityShell';
import { CommunityPage } from '@/routes/CommunityPage';
import { AskProfilePage } from '@/routes/AskProfilePage';
import { MyAskPage } from '@/routes/MyAskPage';
import { RootLayout } from '@/layout/RootLayout';

export const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      { path: '/', element: <LandingPage /> },
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
          { path: 'assess', element: <AssessPage /> },
        ],
      },
      {
        path: '/community',
        element: <CommunityShell />,
        children: [
          { index: true, element: <CommunityPage /> },
          { path: 'p/:id', element: <AskProfilePage /> },
          { path: 'me', element: <MyAskPage /> },
        ],
      },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
]);
