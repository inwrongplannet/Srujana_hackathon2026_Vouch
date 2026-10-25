/**
 * Wraps every route: a new page starts at the top (back and forward keep their place), and the
 * browser tab names the screen, so a presenter can tell tabs apart.
 */
import { useEffect } from 'react';
import { Outlet, ScrollRestoration, useLocation } from 'react-router';

const TITLES: [RegExp, string][] = [
  [/^\/login/, 'Sign in'],
  [/^\/app\/borrower/, 'Borrower · Guided story'],
  [/^\/app\/voucher/, 'Voucher · Guided story'],
  [/^\/app\/lender\/.+/, 'Applicant file · Guided story'],
  [/^\/app\/lender/, 'Lender console · Guided story'],
  [/^\/app\/assess/, 'Assessment desk'],
  [/^\/community\/me/, 'My ask · Community'],
  [/^\/community\/p\//, 'Profile · Community'],
  [/^\/community/, 'Discover · Community'],
];

export function RootLayout() {
  const { pathname } = useLocation();
  useEffect(() => {
    const page = TITLES.find(([re]) => re.test(pathname))?.[1];
    document.title = page ? `${page} · Vouch` : 'Vouch · peer-backed evidence for credit';
  }, [pathname]);
  return (
    <>
      <Outlet />
      <ScrollRestoration />
    </>
  );
}
