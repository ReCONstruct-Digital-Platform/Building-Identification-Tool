const path = require("path");
const BundleTracker = require("webpack-bundle-tracker");

module.exports = {
  context: __dirname,
  entry: {
    main: "./assets/main.ts", // path to our input file
    entry2: "./assets/entry2.ts", // path to our input file
  },
  output: {
    filename: "[name]-[contenthash].js",
    publicPath: "auto", // necessary for CDNs/S3/blob storages
    path: path.resolve(__dirname, "./assets/output/bundles"), // path to our Django static directory
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        loader: "babel-loader",
        options: { presets: ["@babel/preset-env", "@babel/preset-react"] },
      },
      {
        test: /\.tsx?$/,
        use: "ts-loader",
        exclude: /node_modules/,
      },
    ],
  },
  resolve: {
    extensions: [".tsx", ".ts", ".js"],
  },
  plugins: [new BundleTracker({ path: __dirname, filename: "webpack-stats.json" })],
};
