import { extendTheme } from '@chakra-ui/react'

const theme = extendTheme({
  config: {
    initialColorMode: 'dark',
    useSystemColorMode: false,
  },
  styles: {
    global: {
      body: {
        bg: '#0d0d12',
        color: 'white',
      },
    },
  },
  colors: {
    brand: {
      50: '#f5f3ff',
      100: '#ede9fe',
      200: '#ddd6fe',
      300: '#c4b5fd',
      400: '#a78bfa',
      500: '#8b5cf6',
      600: '#7c3aed',
      700: '#6d28d9',
      800: '#5b21b6',
      900: '#4c1d95',
    },
    dark: {
      900: '#0d0d12',
      800: '#18181f',
      700: '#1e1e28',
      600: '#25252f',
      500: '#2d2d3a',
    },
  },
  components: {
    Button: {
      variants: {
        primary: {
          bgGradient: 'linear(to-r, brand.500, pink.500)',
          color: 'white',
          _hover: {
            bgGradient: 'linear(to-r, brand.600, pink.600)',
            transform: 'translateY(-2px)',
            boxShadow: 'lg',
          },
          _active: {
            transform: 'translateY(0)',
          },
        },
        ghost: {
          color: 'gray.400',
          _hover: {
            bg: 'dark.700',
            color: 'white',
          },
        },
      },
    },
    Input: {
      variants: {
        filled: {
          field: {
            bg: 'dark.800',
            borderColor: 'gray.700',
            _hover: {
              bg: 'dark.700',
            },
            _focus: {
              bg: 'dark.700',
              borderColor: 'brand.500',
            },
          },
        },
      },
      defaultProps: {
        variant: 'filled',
      },
    },
    Select: {
      variants: {
        filled: {
          field: {
            bg: 'dark.800',
            borderColor: 'gray.700',
            _hover: {
              bg: 'dark.700',
            },
            _focus: {
              bg: 'dark.700',
              borderColor: 'brand.500',
            },
          },
        },
      },
      defaultProps: {
        variant: 'filled',
      },
    },
    Modal: {
      baseStyle: {
        dialog: {
          bg: 'dark.800',
        },
        overlay: {
          bg: 'blackAlpha.800',
          backdropFilter: 'blur(10px)',
        },
      },
    },
    Card: {
      baseStyle: {
        container: {
          bg: 'dark.700',
          borderRadius: 'xl',
          borderWidth: '1px',
          borderColor: 'gray.800',
        },
      },
    },
  },
})

export default theme
