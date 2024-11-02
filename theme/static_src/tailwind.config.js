/**
 * This is a minimal config.
 *
 * If you need the full config, get it from here:
 * https://unpkg.com/browse/tailwindcss@latest/stubs/defaultConfig.stub.js
 */

module.exports = {
    darkMode: 'class',
    important: true,
    content: [
        /**
         * HTML. Paths to Django template files that will contain Tailwind CSS classes.
         */
        /*  Templates within main app */
        '../../buildings/templates/**/*.html',

        /**
         * JS: If you use Tailwind CSS in JavaScript, uncomment the following lines and make sure
         * patterns match your project structure.
         */
        /* JS 1: Ignore any JavaScript in node_modules folder. */
        '!./node_modules',
        /* JS 2: Process all JavaScript files in the project. */
        '../../buildings/static/**/*.js',

        /**
         * Python: If you use Tailwind CSS classes in Python, uncomment the following line
         * and make sure the pattern below matches your project structure.
         */
        '../../buildings/**/*.py'
    ],
    theme: {
        extend: {
            colors: {
                teal: {
                    '50': '#f3faf8',
                    '100': '#d6f1eb',
                    '200': '#ade2d8',
                    '300': '#7cccbf',
                    '400': '#51b0a4',
                    '500': '#37958a',
                    '600': '#2d7f78',
                    '700': '#25605b',
                    '800': '#224d4b',
                    '900': '#20413f',
                    '950': '#0d2625',
                },
                blue: {
                    '50': '#f1f8fe',
                    '100': '#e2effc',
                    '200': '#bedef9',
                    '300': '#85c3f4',
                    '400': '#379feb',
                    '500': '#1b8adc',
                    '600': '#0e6cbb',
                    '700': '#0d5697',
                    '800': '#0f4a7d',
                    '900': '#123e68',
                    '950': '#0c2745',
                },
                gray: {
                    '50': '#f7f8f7',
                    '100': '#e6eae6',
                    '200': '#cfd8d2',
                    '300': '#abbab4',
                    '400': '#7f948e',
                    '500': '#687876',
                    '600': '#526466',
                    '700': '#465458',
                    '800': '#3d454c',
                    '900': '#383b43',
                    '950': '#22242a',
                },
                slate: {
                    '50': '#f3f5f6',
                    '100': '#e1e7ea',
                    '200': '#c9d2d9',
                    '300': '#a2b3be',
                    '400': '#738b9c',
                    '500': '#60798a',
                    '600': '#495a69',
                    '700': '#404c59',
                    '800': '#3a424b',
                    '900': '#343a42',
                    '950': '#1e2429',
                },
            }
        },
    },
    plugins: [
        /**
         * '@tailwindcss/forms' is the forms plugin that provides a minimal styling
         * for forms. If you don't like it or have own styling for forms,
         * comment the line below to disable '@tailwindcss/forms'.
         */
        require('@tailwindcss/forms'),
        require('@tailwindcss/typography'),
        require('@tailwindcss/aspect-ratio'),
    ]
}
