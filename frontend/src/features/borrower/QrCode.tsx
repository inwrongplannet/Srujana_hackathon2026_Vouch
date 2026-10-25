import { useEffect, useState } from 'react';
import QRCode from 'qrcode';

/** A real, scannable QR for the vouch link, drawn in ink on transparent paper. */
export function QrCode({ value, size = 148 }: { value: string; size?: number }) {
  const [svg, setSvg] = useState('');
  useEffect(() => {
    let alive = true;
    QRCode.toString(value, { type: 'svg', margin: 0, errorCorrectionLevel: 'M', color: { dark: '#16181F', light: '#0000' } }).then((s) => {
      if (alive) setSvg(s);
    });
    return () => {
      alive = false;
    };
  }, [value]);
  return <div style={{ width: size, height: size }} className="[&_svg]:h-full [&_svg]:w-full" aria-label="QR code for the vouch link" role="img" dangerouslySetInnerHTML={{ __html: svg }} />;
}
