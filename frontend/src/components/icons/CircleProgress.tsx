import React, { FC } from "react";
import type { IconBaseProps } from "react-icons";

export const CircleProgress: FC<IconBaseProps> = ({
  size,
  className,
  ...props
}) => (
  <svg
    stroke="currentColor"
    fill="currentColor"
    strokeWidth="0"
    viewBox="0 0 512 512"
    height={size}
    width={size}
    className={className}
    {...props}
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M 464,256 C 464,141.12469 370.87523,48.00009 256,48.00009 141.12477,48.00009 48,141.12469 48,256 c 0,114.87531 93.12477,207.99991 208,207.99991 114.87523,0 208,-93.1246 208,-207.99991 z M 0,256 C 0,114.61501 114.61511,1.1113408e-4 256,1.1113408e-4 397.38489,1.1113408e-4 512,114.61501 512,256 512,397.38499 397.38489,511.99989 256,511.99989 114.61511,511.99989 0,397.38499 0,256 Z"
      style={{ fillOpacity: "0.7" }}
    />
    <path
      d="m 256,160 c 53.01937,0 95.99996,42.98067 95.99996,96 0,53.01933 -42.98059,96 -95.99996,96 -53.01937,0 -95.99996,-42.98067 -95.99996,-96 0,-53.01933 42.98059,-96 95.99996,-96 z"
      style={{ fillOpacity: "1" }}
    />
    <path d="m 241.06339,0 -0.34904,48.553209 c 93.28777,0 169.00602,48.840401 202.62834,116.967271 11.41982,23.1393 20.11917,49.2212 20.11917,75.4016 L 512,240.75 C 512,140.43915 451.62582,56.969771 356.0897,20.305676 336.48904,12.783491 321.64678,6.8622077 298.07108,3.4404686 281.70119,1.0645691 256.82772,0 241.06339,0 Z" />
  </svg>
);
