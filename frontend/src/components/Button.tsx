import type { ButtonHTMLAttributes, ReactNode } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode
  icon?: ReactNode
  variant?: 'primary' | 'secondary'
}

export function Button({ children, icon, variant = 'primary', ...props }: ButtonProps) {
  return (
    <button className={`button button--${variant}`} type="button" {...props}>
      {icon}
      <span>{children}</span>
    </button>
  )
}
